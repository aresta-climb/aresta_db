import os
import pytest
import boto3
from pathlib import Path
from unittest.mock import patch, call
from moto import mock_aws
import requests_mock
from botocore.exceptions import ClientError

# Como estamos fazendo TDD, importaremos a classe principal
# que será implementada em update_serving.py
from update_serving import Deployer, CloudflarePurger, get_db_version

from aresta_api.proto.generated import serving_pb2

def test_get_db_version(tmp_path):
    if "DB_VERSION" in os.environ:
        del os.environ["DB_VERSION"]
        
    with patch("update_serving.Path") as mock_path:
        # Simula o caminho base_dir.exists()
        mock_base = mock_path.return_value.resolve.return_value.parent.parent.__truediv__.return_value
        mock_base.exists.return_value = True
        
        # Simula a iteração glob
        class MockFile:
            def __init__(self, name): self.name = name
            
        mock_base.glob.return_value = [
            MockFile("0001_initial.py"),
            MockFile("0002_add_field.py"),
            MockFile("0003_algo_test.py"), # Será ignorado
            MockFile("ignore.txt"),       # Não tem dígito, será ignorado
            MockFile("0010_latest.py")
        ]
        
        assert get_db_version() == "v10"

def test_get_local_manifest_checkout_failure(deployer):
    # Garante que um erro no checkout do git blobless é suprimido silenciosamente
    # e emite um FileNotFoundError nativo se o arquivo realmente não existir localmente.
    import subprocess
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        with pytest.raises(FileNotFoundError, match="Manifesto local não encontrado"):
            deployer._get_local_manifest()

@pytest.fixture
def aws_credentials():
    """Mock AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["R2_ACCOUNT_ID"] = "dummy_account"
    os.environ["R2_BUCKET"] = "test-bucket"

@pytest.fixture
def mock_s3(aws_credentials):
    with mock_aws():
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket="test-bucket")
        yield conn

@pytest.fixture
def deployer(tmp_path):
    os.environ["DB_VERSION"] = "v1"
    # Cria diretório "generated" local simulado
    gen_dir = tmp_path / "generated"
    gen_dir.mkdir()
    d = Deployer(generated_dir=gen_dir)
    return d

def criar_manifesto(arquivos: dict) -> bytes:
    m = serving_pb2.ArquivosServing()
    for rel_path, checksum in arquivos.items():
        a = m.arquivos.add()
        a.caminho_relativo = rel_path
        a.checksum_sha256 = checksum
    return m.SerializeToString()

def test_full_deploy_fallback(mock_s3, deployer, tmp_path):
    """Quando o remoto não tem manifesto, faz full deploy."""
    # Prepara manifesto local
    local_arquivos = {
        "indice.binarypb": "hash1",
        "pico/compilado.binarypb": "hash2"
    }
    manifest_bytes = criar_manifesto(local_arquivos)
    (deployer.generated_dir / "arquivos_serving.binarypb").write_bytes(manifest_bytes)
    
    # Prepara arquivos locais físicos (mock)
    (deployer.generated_dir / "indice.binarypb").write_bytes(b"content1")
    (deployer.generated_dir / "pico").mkdir()
    (deployer.generated_dir / "pico/compilado.binarypb").write_bytes(b"content2")

    with patch('subprocess.run') as mock_run:
        with requests_mock.Mocker() as m:
            m.post('https://api.cloudflare.com/client/v4/zones/fake-zone/purge_cache', text='{"success":true}')
            
            os.environ["CLOUDFLARE_ZONE_ID"] = "fake-zone"
            os.environ["CLOUDFLARE_CACHE_PURGE_API_TOKEN"] = "fake-token"
            
            deployer.execute()
            
            # Deve ter chamado o git checkout para baixar TUDO
            mock_run.assert_any_call(["git", "checkout", "HEAD", "--", "generated/"], check=True)
            
            # Valida arquivos no S3
            objs = mock_s3.list_objects_v2(Bucket="test-bucket")["Contents"]
            keys = {o["Key"] for o in objs}
            assert keys == {
                "v1/arquivos_serving.binarypb",
                "v1/indice.binarypb",
                "v1/pico/compilado.binarypb"
            }

            # Valida request de purge
            assert m.called
            req = m.request_history[0]
            assert req.headers["Authorization"] == "Bearer fake-token"
            assert req.json() == {
                "files": [
                    "https://cdn.aresta.app/v1/indice.binarypb",
                    "https://cdn.aresta.app/v1/arquivos_serving.binarypb"
                ]
            }

def test_delta_deploy(mock_s3, deployer, tmp_path):
    """Compara local com remoto e envia apenas deltas."""
    
    # 1. Coloca o manifesto remoto no mock S3
    remoto_arquivos = {
        "indice.binarypb": "hash_old",
        "mantido.png": "hash_same",
        "deletado.txt": "hash_del"
    }
    mock_s3.put_object(
        Bucket="test-bucket", 
        Key="v1/arquivos_serving.binarypb", 
        Body=criar_manifesto(remoto_arquivos)
    )

    # 2. Prepara o manifesto local
    local_arquivos = {
        "indice.binarypb": "hash_new",     # Modificado
        "mantido.png": "hash_same",        # Inalterado
        "novo_pico/compilado.binarypb": "hash_add" # Adicionado
    }
    manifest_bytes = criar_manifesto(local_arquivos)
    (deployer.generated_dir / "arquivos_serving.binarypb").write_bytes(manifest_bytes)
    
    # Arquivos físicos para upload
    (deployer.generated_dir / "indice.binarypb").write_bytes(b"new1")
    (deployer.generated_dir / "novo_pico").mkdir()
    (deployer.generated_dir / "novo_pico/compilado.binarypb").write_bytes(b"new2")

    with patch('subprocess.run') as mock_run:
        with requests_mock.Mocker() as m:
            m.post('https://api.cloudflare.com/client/v4/zones/fake-zone/purge_cache', text='{"success":true}')
            os.environ["CLOUDFLARE_ZONE_ID"] = "fake-zone"
            os.environ["CLOUDFLARE_CACHE_PURGE_API_TOKEN"] = "fake-token"
            
            deployer.execute()
            
            # Deve ter chamado o git checkout APENAS para os modificados/adicionados e o próprio manifesto
            # O manifesto serving já existe localmente pois o python rodou, mas é mais fácil mandar o path todo
            # pro git checkout
            mock_run.assert_any_call(["git", "checkout", "HEAD", "--", "generated/arquivos_serving.binarypb", "generated/indice.binarypb", "generated/novo_pico/compilado.binarypb"], check=True)
            
            # Valida arquivos no S3 (mantido.png não existe no mock real mas estaria lá antes. Como deletamos,
            # ele chama o delete_object)
            # Vamos checar se o boto3 client teve os metodos chamados:
            
            objs = mock_s3.list_objects_v2(Bucket="test-bucket").get("Contents", [])
            keys = {o["Key"] for o in objs}
            assert "v1/indice.binarypb" in keys
            assert "v1/novo_pico/compilado.binarypb" in keys
            # deletado.txt NÃO deve estar, se eu tivesse posto lá
            assert "v1/deletado.txt" not in keys

            # Valida Purge Cache
            assert m.called
            req = m.request_history[0]
            assert req.json() == {
                "files": [
                    "https://cdn.aresta.app/v1/indice.binarypb",
                    "https://cdn.aresta.app/v1/arquivos_serving.binarypb"
                ]
            }

def test_purge_skip_if_no_credentials():
    purger = CloudflarePurger()
    if "CLOUDFLARE_ZONE_ID" in os.environ:
        del os.environ["CLOUDFLARE_ZONE_ID"]
    with pytest.raises(ValueError, match="Credenciais do Cloudflare ausentes"):
        purger.purge_manifests("v1")

def test_deployer_with_r2_endpoint(tmp_path):
    os.environ["R2_ENDPOINT_URL"] = "http://fake-endpoint"
    d = Deployer(generated_dir=tmp_path)
    assert d.s3._endpoint.host == "http://fake-endpoint"
    del os.environ["R2_ENDPOINT_URL"]

def test_get_remote_manifest_boto3_error(mock_s3, deployer):
    # Simula um erro que não seja NoSuchKey
    with patch.object(deployer.s3, 'get_object', side_effect=ClientError({'Error': {'Code': 'AccessDenied'}}, 'GetObject')):
        with pytest.raises(ClientError):
            deployer._get_remote_manifest()

def test_get_local_manifest_not_found(deployer):
    with pytest.raises(FileNotFoundError, match="Manifesto local não encontrado"):
        deployer._get_local_manifest()

def test_delta_deploy_no_changes(mock_s3, deployer, capsys):
    arquivos = {"indice.binarypb": "same", "compilado.binarypb": "same"}
    manifest_bytes = criar_manifesto(arquivos)
    mock_s3.put_object(Bucket="test-bucket", Key="v1/arquivos_serving.binarypb", Body=manifest_bytes)
    (deployer.generated_dir / "arquivos_serving.binarypb").write_bytes(manifest_bytes)
    
    with patch('subprocess.run') as mock_run:
        deployer.execute()
        # Deve ter sido chamado pelo menos 1 vez (pro arquivos_serving)
        mock_run.assert_called_with(["git", "checkout", "HEAD", "--", "generated/arquivos_serving.binarypb"], check=True, capture_output=True)
        # Nenhuma outra chamada para baixar deltas
        assert mock_run.call_count == 1
        
    out, _ = capsys.readouterr()
    assert "Nenhum arquivo modificado. Deploy pulado." in out

def test_delta_deploy_with_indice_in_modified(mock_s3, deployer):
    remoto = {"indice.binarypb": "old"}
    mock_s3.put_object(Bucket="test-bucket", Key="v1/arquivos_serving.binarypb", Body=criar_manifesto(remoto))
    
    local = {"indice.binarypb": "new"}
    (deployer.generated_dir / "arquivos_serving.binarypb").write_bytes(criar_manifesto(local))
    (deployer.generated_dir / "indice.binarypb").write_bytes(b"content")
    
    with patch('subprocess.run') as mock_run:
        with requests_mock.Mocker() as m:
            m.post('https://api.cloudflare.com/client/v4/zones/fake-zone/purge_cache', text='{"success":true}')
            os.environ["CLOUDFLARE_ZONE_ID"] = "fake-zone"
            os.environ["CLOUDFLARE_CACHE_PURGE_API_TOKEN"] = "fake-token"
            deployer.execute()
            mock_run.assert_any_call(["git", "checkout", "HEAD", "--", "generated/arquivos_serving.binarypb", "generated/indice.binarypb"], check=True)

def test_delta_deploy_with_compilado_only(mock_s3, deployer):
    # Remote has same indice, different compilado
    remoto = {"indice.binarypb": "same", "compilado.binarypb": "old"}
    mock_s3.put_object(Bucket="test-bucket", Key="v1/arquivos_serving.binarypb", Body=criar_manifesto(remoto))
    
    # Local has same indice, new compilado
    local = {"indice.binarypb": "same", "compilado.binarypb": "new"}
    (deployer.generated_dir / "arquivos_serving.binarypb").write_bytes(criar_manifesto(local))
    (deployer.generated_dir / "compilado.binarypb").write_bytes(b"content")
    
    with patch('subprocess.run') as mock_run:
        with requests_mock.Mocker() as m:
            m.post('https://api.cloudflare.com/client/v4/zones/fake-zone/purge_cache', text='{"success":true}')
            os.environ["CLOUDFLARE_ZONE_ID"] = "fake-zone"
            os.environ["CLOUDFLARE_CACHE_PURGE_API_TOKEN"] = "fake-token"
            deployer.execute()
            # Indice deve ser adicionado à lista forçosamente
            mock_run.assert_any_call(["git", "checkout", "HEAD", "--", "generated/arquivos_serving.binarypb", "generated/compilado.binarypb", "generated/indice.binarypb"], check=True)
