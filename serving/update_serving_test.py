import os
import pytest
import subprocess
import urllib.error
import json
from pathlib import Path
from unittest.mock import patch, call, MagicMock

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
def deployer(tmp_path):
    gen_dir = tmp_path / "generated"
    gen_dir.mkdir()
    
    with patch('update_serving.get_db_version', return_value="v1"):
        d = Deployer(generated_dir=gen_dir)
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

def setup_mock_aws_cmd(mock_aws_cmd_func, remote_manifest_data=None):
    uploaded = set()
    deleted = set()
    def side_effect(*args):
        cmd_type = args[0]
        if cmd_type == "cp":
            src = args[1]
            dest = args[2]
            if dest == "temp_remote_manifest.yaml":
                if remote_manifest_data is None:
                    raise subprocess.CalledProcessError(1, ["aws"])
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(remote_manifest_data)
            else:
                uploaded.add(dest)
        elif cmd_type == "rm":
            deleted.add(args[1])
            
    mock_aws_cmd_func.side_effect = side_effect
    return uploaded, deleted

def test_full_deploy_fallback(deployer, tmp_path):
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

    with patch.object(deployer, '_aws_cmd') as mock_aws:
        uploaded, _ = setup_mock_aws_cmd(mock_aws, None) # None = Sem manifesto remoto
        with patch('subprocess.run') as mock_run:
            with patch.object(deployer.purger, 'purge_manifests'):
                deployer.execute()
                
                # Checa se o fallback checkout foi chamado
                mock_run.assert_any_call(["git", "checkout", "HEAD", "--ignore-skip-worktree-bits", "--", "generated/"], check=True)
                
                # Valida S3
                assert f"s3://{deployer.bucket}/v1/arquivos_serving.yaml" in uploaded
                assert f"s3://{deployer.bucket}/v1/indice.binarypb" in uploaded
                assert f"s3://{deployer.bucket}/v1/pico/compilado.binarypb" in uploaded

def test_delta_deploy(deployer, tmp_path):
    remoto_arquivos = {
        "indice.binarypb": "hash_old",
        "mantido.png": "hash_same",
        "deletado.txt": "hash_del"
    }
    remote_data = criar_manifesto(remoto_arquivos)

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

    with patch.object(deployer, '_aws_cmd') as mock_aws:
        uploaded, deleted = setup_mock_aws_cmd(mock_aws, remote_data)
        with patch('subprocess.run') as mock_run:
            with patch.object(deployer.purger, 'purge_manifests'):
                deployer.execute()
                
                mock_run.assert_any_call(["git", "checkout", "HEAD", "--ignore-skip-worktree-bits", "--", "generated/arquivos_serving.yaml", "generated/indice.binarypb", "generated/novo_pico/compilado.binarypb"], check=True)
                
                assert f"s3://{deployer.bucket}/v1/indice.binarypb" in uploaded
                assert f"s3://{deployer.bucket}/v1/novo_pico/compilado.binarypb" in uploaded
                assert f"s3://{deployer.bucket}/v1/arquivos_serving.yaml" in uploaded
                
                assert f"s3://{deployer.bucket}/v1/deletado.txt" in deleted

def test_delta_deploy_no_changes(deployer, capsys):
    arquivos = {"indice.binarypb": "same", "compilado.binarypb": "same"}
    data = criar_manifesto(arquivos)
    (deployer.generated_dir / "arquivos_serving.yaml").write_text(data, encoding="utf-8")
    
    with patch.object(deployer, '_aws_cmd') as mock_aws:
        setup_mock_aws_cmd(mock_aws, data)
        with patch('subprocess.run') as mock_run:
            deployer.execute()
            
    out, _ = capsys.readouterr()
    assert "Nenhum arquivo modificado. Deploy pulado." in out

def test_delta_deploy_with_indice_in_modified(deployer):
    remoto = {"indice.binarypb": "old"}
    remote_data = criar_manifesto(remoto)
    
    local = {"indice.binarypb": "new"}
    (deployer.generated_dir / "arquivos_serving.yaml").write_text(criar_manifesto(local), encoding="utf-8")
    (deployer.generated_dir / "indice.binarypb").write_bytes(b"content")
    
    with patch.object(deployer, '_aws_cmd') as mock_aws:
        setup_mock_aws_cmd(mock_aws, remote_data)
        with patch('subprocess.run') as mock_run:
            with patch.object(deployer.purger, 'purge_manifests'):
                deployer.execute()
                mock_run.assert_any_call(["git", "checkout", "HEAD", "--ignore-skip-worktree-bits", "--", "generated/arquivos_serving.yaml", "generated/indice.binarypb"], check=True)

def test_delta_deploy_with_compilado_only(deployer):
    remoto = {"indice.binarypb": "same", "compilado.binarypb": "old"}
    remote_data = criar_manifesto(remoto)
    
    local = {"indice.binarypb": "same", "compilado.binarypb": "new"}
    (deployer.generated_dir / "arquivos_serving.yaml").write_text(criar_manifesto(local), encoding="utf-8")
    (deployer.generated_dir / "compilado.binarypb").write_bytes(b"content")
    
    with patch.object(deployer, '_aws_cmd') as mock_aws:
        setup_mock_aws_cmd(mock_aws, remote_data)
        with patch('subprocess.run') as mock_run:
            with patch.object(deployer.purger, 'purge_manifests'):
                deployer.execute()
                mock_run.assert_any_call(["git", "checkout", "HEAD", "--ignore-skip-worktree-bits", "--", "generated/arquivos_serving.yaml", "generated/compilado.binarypb", "generated/indice.binarypb"], check=True)

def test_aws_cmd_env_metadata_disabled(deployer):
    with patch('subprocess.run') as mock_run:
        deployer._aws_cmd("cp", "a", "b")
        
        mock_run.assert_called_once()
        kwargs = mock_run.call_args[1]
        assert "env" in kwargs
        assert kwargs["env"].get("AWS_EC2_METADATA_DISABLED") == "true"
