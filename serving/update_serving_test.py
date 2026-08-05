# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import os
import pytest
import boto3
import urllib.error
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from moto import mock_aws

# Como estamos fazendo TDD, importaremos a classe principal
# que será implementada em update_serving.py
from update_serving import Deployer, CloudflarePurger, get_db_version, load_arquivos_serving

def test_get_db_version(tmp_path):
    if "DB_VERSION" in os.environ:
        del os.environ["DB_VERSION"]
        
    with patch("update_serving.Path") as mock_path, patch("subprocess.run") as mock_run:
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

def criar_manifesto(arquivos_dict: dict) -> str:
    lines = ["arquivos:"]
    for k, v in arquivos_dict.items():
        lines.append(f"- caminho_relativo: {k}")
        lines.append(f"  checksum_sha256: {v}")
    return "\n".join(lines)

def test_load_arquivos_serving():
    data = criar_manifesto({"a.txt": "hashA", "b.png": "hashB"})
    parsed = load_arquivos_serving(data)
    assert parsed["arquivos"][0]["caminho_relativo"] == "a.txt"
    assert parsed["arquivos"][0]["checksum_sha256"] == "hashA"
    assert parsed["arquivos"][1]["caminho_relativo"] == "b.png"
    assert parsed["arquivos"][1]["checksum_sha256"] == "hashB"

@pytest.fixture
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["R2_BUCKET"] = "aresta"
    if "R2_ENDPOINT_URL" in os.environ:
        del os.environ["R2_ENDPOINT_URL"]

@pytest.fixture
def mock_s3(aws_credentials):
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="aresta")
        yield s3

@pytest.fixture
def deployer(tmp_path, aws_credentials, mock_s3):
    gen_dir = tmp_path / "generated"
    gen_dir.mkdir()
    
    with patch('update_serving.get_db_version', return_value="v1"):
        d = Deployer(generated_dir=gen_dir)
        d.s3 = mock_s3
        return d

def test_cloudflare_purger_success():
    purger = CloudflarePurger()
    os.environ["CLOUDFLARE_ZONE_ID"] = "fake-zone"
    os.environ["CLOUDFLARE_CACHE_PURGE_API_TOKEN"] = "fake-token"
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        purger.purge_manifests("v1")
        
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.headers["Authorization"] == "Bearer fake-token"
        assert req.headers["Content-type"] == "application/json"
        
        payload = json.loads(req.data.decode("utf-8"))
        assert payload == {
            "files": [
                "https://serving.arestaclimb.com/v1/indice.binarypb",
                "https://serving.arestaclimb.com/v1/indice.yaml",
                "https://serving.arestaclimb.com/v1/arquivos_serving.yaml"
            ]
        }

def test_cloudflare_purger_missing_credentials():
    purger = CloudflarePurger()
    if "CLOUDFLARE_ZONE_ID" in os.environ: del os.environ["CLOUDFLARE_ZONE_ID"]
    if "CLOUDFLARE_CACHE_PURGE_API_TOKEN" in os.environ: del os.environ["CLOUDFLARE_CACHE_PURGE_API_TOKEN"]
    
    with pytest.raises(ValueError, match="Credenciais do Cloudflare ausentes"):
        purger.purge_manifests("v1")

def test_cloudflare_purger_http_error():
    purger = CloudflarePurger()
    os.environ["CLOUDFLARE_ZONE_ID"] = "fake-zone"
    os.environ["CLOUDFLARE_CACHE_PURGE_API_TOKEN"] = "fake-token"
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError("url", 403, "Forbidden", {}, None)
        with pytest.raises(urllib.error.HTTPError):
            purger.purge_manifests("v1")

def test_full_deploy_fallback(deployer, tmp_path, mock_s3):
    local_arquivos = {
        "indice.binarypb": "hash1",
        "pico/compilado.binarypb": "hash2"
    }
    
    # Prepara manifesto local
    manifest_bytes = criar_manifesto(local_arquivos).encode("utf-8")
    (deployer.generated_dir / "arquivos_serving.yaml").write_bytes(manifest_bytes)
    
    # Prepara arquivos locais físicos
    (deployer.generated_dir / "indice.binarypb").write_bytes(b"content1")
    (deployer.generated_dir / "pico").mkdir()
    (deployer.generated_dir / "pico/compilado.binarypb").write_bytes(b"content2")

    with patch('subprocess.run') as mock_run:
        with patch.object(deployer.purger, 'purge_manifests'):
            deployer.execute()
            
            # Checa se o fallback checkout foi chamado
            mock_run.assert_any_call(["git", "checkout", "HEAD", "--ignore-skip-worktree-bits", "--", "generated/"], check=True)
            
            # Valida S3
            objs = mock_s3.list_objects_v2(Bucket="aresta").get("Contents", [])
            keys = {o["Key"] for o in objs}
            assert "v1/arquivos_serving.yaml" in keys
            assert "v1/indice.binarypb" in keys
            assert "v1/pico/compilado.binarypb" in keys

def test_delta_deploy(deployer, tmp_path, mock_s3):
    remoto_arquivos = {
        "indice.binarypb": "hash_old",
        "mantido.png": "hash_same",
        "deletado.txt": "hash_del"
    }
    mock_s3.put_object(
        Bucket="aresta", 
        Key="v1/arquivos_serving.yaml", 
        Body=criar_manifesto(remoto_arquivos).encode("utf-8")
    )

    local_arquivos = {
        "indice.binarypb": "hash_new",     # Modificado
        "mantido.png": "hash_same",        # Inalterado
        "novo_pico/compilado.binarypb": "hash_add" # Adicionado
    }
    manifest_bytes = criar_manifesto(local_arquivos).encode("utf-8")
    (deployer.generated_dir / "arquivos_serving.yaml").write_bytes(manifest_bytes)
    
    (deployer.generated_dir / "indice.binarypb").write_bytes(b"new1")
    (deployer.generated_dir / "novo_pico").mkdir()
    (deployer.generated_dir / "novo_pico/compilado.binarypb").write_bytes(b"new2")

    with patch('subprocess.run') as mock_run:
        with patch.object(deployer.purger, 'purge_manifests'):
            deployer.execute()
            
            mock_run.assert_any_call(["git", "checkout", "HEAD", "--ignore-skip-worktree-bits", "--", "generated/arquivos_serving.yaml", "generated/indice.binarypb", "generated/novo_pico/compilado.binarypb"], check=True)
            
            objs = mock_s3.list_objects_v2(Bucket="aresta").get("Contents", [])
            keys = {o["Key"] for o in objs}
            assert "v1/indice.binarypb" in keys
            assert "v1/novo_pico/compilado.binarypb" in keys
            assert "v1/arquivos_serving.yaml" in keys
            assert "v1/deletado.txt" not in keys

def test_delta_deploy_no_changes(deployer, capsys, mock_s3):
    arquivos = {"indice.binarypb": "same", "compilado.binarypb": "same"}
    data = criar_manifesto(arquivos).encode("utf-8")
    mock_s3.put_object(Bucket="aresta", Key="v1/arquivos_serving.yaml", Body=data)
    (deployer.generated_dir / "arquivos_serving.yaml").write_bytes(data)
    
    with patch('subprocess.run') as mock_run:
        deployer.execute()
        
    out, _ = capsys.readouterr()
    assert "Nenhum arquivo modificado. Deploy pulado." in out

def test_delta_deploy_with_indice_in_modified(deployer, mock_s3):
    remoto = {"indice.binarypb": "old"}
    mock_s3.put_object(Bucket="aresta", Key="v1/arquivos_serving.yaml", Body=criar_manifesto(remoto).encode("utf-8"))
    
    local = {"indice.binarypb": "new"}
    (deployer.generated_dir / "arquivos_serving.yaml").write_text(criar_manifesto(local), encoding="utf-8")
    (deployer.generated_dir / "indice.binarypb").write_bytes(b"content")
    
    with patch('subprocess.run') as mock_run:
        with patch.object(deployer.purger, 'purge_manifests'):
            deployer.execute()
            mock_run.assert_any_call(["git", "checkout", "HEAD", "--ignore-skip-worktree-bits", "--", "generated/arquivos_serving.yaml", "generated/indice.binarypb"], check=True)

def test_delta_deploy_with_compilado_only(deployer, mock_s3):
    remoto = {"indice.binarypb": "same", "compilado.binarypb": "old"}
    mock_s3.put_object(Bucket="aresta", Key="v1/arquivos_serving.yaml", Body=criar_manifesto(remoto).encode("utf-8"))
    
    local = {"indice.binarypb": "same", "compilado.binarypb": "new"}
    (deployer.generated_dir / "arquivos_serving.yaml").write_text(criar_manifesto(local), encoding="utf-8")
    (deployer.generated_dir / "compilado.binarypb").write_bytes(b"content")
    
    with patch('subprocess.run') as mock_run:
        with patch.object(deployer.purger, 'purge_manifests'):
            deployer.execute()
            mock_run.assert_any_call(["git", "checkout", "HEAD", "--ignore-skip-worktree-bits", "--", "generated/arquivos_serving.yaml", "generated/compilado.binarypb", "generated/indice.binarypb"], check=True)
