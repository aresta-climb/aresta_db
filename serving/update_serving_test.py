# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import json
import os
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from serving.update_serving import (
    CloudflarePurger,
    Deployer,
    _migracao_afeta_serving,
    get_db_version,
    load_arquivos_serving,
)


def test_migracao_afeta_serving_casos_borda(tmp_path: Path) -> None:
    # Objeto sem read_text
    assert _migracao_afeta_serving(object()) is True

    # Arquivo com erro de sintaxe Python
    arq_invalido = tmp_path / "invalido.py"
    arq_invalido.write_text("def quebrado(:\n", encoding="utf-8")
    assert _migracao_afeta_serving(arq_invalido) is True


def test_get_db_version(tmp_path: Path) -> None:
    if "DB_VERSION" in os.environ:
        del os.environ["DB_VERSION"]

    with patch("serving.update_serving.Path") as mock_path:
        mock_base = (
            mock_path.return_value.resolve.return_value.parent.parent.__truediv__.return_value
        )
        mock_base.exists.return_value = True

        class MockFile:
            def __init__(self, name: str) -> None:
                self.name = name

        mock_base.glob.return_value = [
            MockFile("0001_initial.py"),
            MockFile("0002_add_field.py"),
            MockFile("0003_algo_test.py"),  # Será ignorado
            MockFile("ignore.txt"),  # Não tem dígito, será ignorado
            MockFile("0010_latest.py"),
        ]

        assert get_db_version() == "v10"


def test_get_db_version_ignora_migracao_database_only(tmp_path: Path) -> None:
    """Garante que migrações que declaram AFETA_VERSAO_SERVING = False não incrementem a versão de serving."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    # Migração 4 normal (afeta serving)
    (migracoes_dir / "0004_adicionar_campos.py").write_text(
        "# Migração normal\nAFETA_VERSAO_SERVING = True\n", encoding="utf-8"
    )

    # Migração 5 database-only com type annotation (não afeta serving)
    (migracoes_dir / "0005_migrar_uids_e_rotulos.py").write_text(
        "# Migração restrita ao banco de dados interno\nAFETA_VERSAO_SERVING: bool = False\n",
        encoding="utf-8",
    )

    # Migração 6 database-only com atribuição simples (não afeta serving)
    (migracoes_dir / "0006_outra_migracao_interna.py").write_text(
        "AFETA_VERSAO_SERVING = False\n",
        encoding="utf-8",
    )

    # Teste de migração (ignorado por convenção _test.py)
    (migracoes_dir / "0005_migrar_uids_e_rotulos_test.py").write_text("", encoding="utf-8")

    with patch("serving.update_serving.Path") as mock_path:
        mock_path.return_value.resolve.return_value.parent.parent.__truediv__.return_value = (
            migracoes_dir
        )
        assert get_db_version() == "v4"


def criar_manifesto(arquivos_dict: dict[str, str]) -> str:
    lines = ["arquivos:"]
    for k, v in arquivos_dict.items():
        lines.append(f"- caminho_relativo: {k}")
        lines.append(f"  checksum_sha256: {v}")
    return "\n".join(lines)


def test_load_arquivos_serving() -> None:
    data = criar_manifesto({"a.txt": "hashA", "b.png": "hashB"})
    parsed = load_arquivos_serving(data)
    assert parsed["arquivos"][0]["caminho_relativo"] == "a.txt"
    assert parsed["arquivos"][0]["checksum_sha256"] == "hashA"
    assert parsed["arquivos"][1]["caminho_relativo"] == "b.png"
    assert parsed["arquivos"][1]["checksum_sha256"] == "hashB"


@pytest.fixture
def aws_credentials() -> None:
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["R2_BUCKET"] = "aresta"
    if "R2_ENDPOINT_URL" in os.environ:
        del os.environ["R2_ENDPOINT_URL"]


@pytest.fixture
def mock_s3(aws_credentials: None):
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="aresta")
        yield s3


@pytest.fixture
def deployer(tmp_path: Path, aws_credentials: None, mock_s3) -> Deployer:
    gen_dir = tmp_path / "generated"
    gen_dir.mkdir()

    with patch("serving.update_serving.get_db_version", return_value="v1"):
        d = Deployer(generated_dir=gen_dir)
        d.s3 = mock_s3
        return d


def test_deployer_init_with_endpoint(
    tmp_path: Path, aws_credentials: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://fake-r2.cloudflarestorage.com")
    with (
        patch("serving.update_serving.get_db_version", return_value="v1"),
        patch("serving.update_serving.boto3.client") as mock_boto,
    ):
        Deployer(generated_dir=tmp_path)
        assert mock_boto.call_args[1]["endpoint_url"] == "https://fake-r2.cloudflarestorage.com"


def test_cloudflare_purger_success() -> None:
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
                "https://serving.arestaclimb.com/v1/arquivos_serving.yaml",
                "https://serving.arestaclimb.com/v1/catalogo.db",
            ]
        }


def test_cloudflare_purger_missing_credentials() -> None:
    purger = CloudflarePurger()
    if "CLOUDFLARE_ZONE_ID" in os.environ:
        del os.environ["CLOUDFLARE_ZONE_ID"]
    if "CLOUDFLARE_CACHE_PURGE_API_TOKEN" in os.environ:
        del os.environ["CLOUDFLARE_CACHE_PURGE_API_TOKEN"]

    with pytest.raises(ValueError, match="Credenciais do Cloudflare ausentes"):
        purger.purge_manifests("v1")


def test_cloudflare_purger_http_error() -> None:
    purger = CloudflarePurger()
    os.environ["CLOUDFLARE_ZONE_ID"] = "fake-zone"
    os.environ["CLOUDFLARE_CACHE_PURGE_API_TOKEN"] = "fake-token"

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError("url", 403, "Forbidden", {}, None)  # type: ignore[arg-type]
        with pytest.raises(urllib.error.HTTPError):
            purger.purge_manifests("v1")


def test_get_remote_manifest_other_client_error(deployer: Deployer) -> None:
    deployer.s3 = MagicMock()
    deployer.s3.get_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Denied"}}, "GetObject"
    )
    with pytest.raises(ClientError):
        deployer._get_remote_manifest()


def test_get_local_manifest_not_found(deployer: Deployer) -> None:
    with pytest.raises(FileNotFoundError, match="Manifesto local não encontrado"):
        deployer._get_local_manifest()


def test_full_deploy_fallback(deployer: Deployer, tmp_path: Path, mock_s3) -> None:
    local_arquivos = {
        "indice.binarypb": "hash1",
        "catalogo.db": "hash_cat",
        "pico/compilado.binarypb": "hash2",
    }

    manifest_bytes = criar_manifesto(local_arquivos).encode("utf-8")
    (deployer.generated_dir / "arquivos_serving.yaml").write_bytes(manifest_bytes)

    (deployer.generated_dir / "indice.binarypb").write_bytes(b"content1")
    (deployer.generated_dir / "catalogo.db").write_bytes(b"sqlite-new")
    (deployer.generated_dir / "pico").mkdir()
    (deployer.generated_dir / "pico/compilado.binarypb").write_bytes(b"content2")

    with (
        patch("subprocess.run") as mock_run,
        patch("serving.update_serving.sincronizar_catalogo_d1") as mock_sync_d1,
        patch.object(deployer.purger, "purge_manifests"),
    ):
        deployer.execute()

        mock_run.assert_any_call(
            ["git", "checkout", "HEAD", "--ignore-skip-worktree-bits", "--", "generated/"],
            check=True,
        )
        mock_sync_d1.assert_called_once_with(
            caminho_catalogo_novo=deployer.generated_dir / "catalogo.db",
            caminho_catalogo_anterior_r2=None,
        )

        objs = mock_s3.list_objects_v2(Bucket="aresta").get("Contents", [])
        keys = {o["Key"] for o in objs}
        assert "v1/arquivos_serving.yaml" in keys
        assert "v1/indice.binarypb" in keys
        assert "v1/catalogo.db" in keys
        assert "v1/pico/compilado.binarypb" in keys


def test_delta_deploy_sincroniza_d1_antes_do_upload_r2(
    deployer: Deployer, tmp_path: Path, mock_s3
) -> None:
    remoto_arquivos = {
        "indice.binarypb": "hash_old",
        "catalogo.db": "hash_cat_old",
        "mantido.png": "hash_same",
        "deletado.txt": "hash_del",
    }
    mock_s3.put_object(
        Bucket="aresta",
        Key="v1/arquivos_serving.yaml",
        Body=criar_manifesto(remoto_arquivos).encode("utf-8"),
    )
    mock_s3.put_object(
        Bucket="aresta",
        Key="v1/catalogo.db",
        Body=b"sqlite-old-from-r2",
    )

    local_arquivos = {
        "indice.binarypb": "hash_new",
        "catalogo.db": "hash_cat_new",
        "mantido.png": "hash_same",
        "novo_pico/compilado.binarypb": "hash_add",
    }
    manifest_bytes = criar_manifesto(local_arquivos).encode("utf-8")
    (deployer.generated_dir / "arquivos_serving.yaml").write_bytes(manifest_bytes)

    (deployer.generated_dir / "indice.binarypb").write_bytes(b"new1")
    (deployer.generated_dir / "catalogo.db").write_bytes(b"sqlite-new-local")
    (deployer.generated_dir / "novo_pico").mkdir()
    (deployer.generated_dir / "novo_pico/compilado.binarypb").write_bytes(b"new2")

    bytes_anterior_recebido: list[bytes] = []

    def _verificar_sync_d1(
        caminho_catalogo_novo: Path, caminho_catalogo_anterior_r2: Path | None
    ) -> str:
        assert caminho_catalogo_anterior_r2 is not None
        bytes_anterior_recebido.append(caminho_catalogo_anterior_r2.read_bytes())
        # Garante que no momento do sync D1 o R2 ainda contém o catalogo.db antigo!
        obj_atual_r2 = mock_s3.get_object(Bucket="aresta", Key="v1/catalogo.db")
        assert obj_atual_r2["Body"].read() == b"sqlite-old-from-r2"
        return "delta"

    with (
        patch("subprocess.run") as mock_run,
        patch(
            "serving.update_serving.sincronizar_catalogo_d1",
            side_effect=_verificar_sync_d1,
        ) as mock_sync_d1,
        patch.object(deployer.purger, "purge_manifests"),
    ):
        deployer.execute()

        assert mock_sync_d1.call_count == 1
        assert bytes_anterior_recebido == [b"sqlite-old-from-r2"]

        mock_run.assert_any_call(
            [
                "git",
                "checkout",
                "HEAD",
                "--ignore-skip-worktree-bits",
                "--",
                "generated/arquivos_serving.yaml",
                "generated/catalogo.db",
                "generated/indice.binarypb",
                "generated/novo_pico/compilado.binarypb",
            ],
            check=True,
        )

        # Após o sync D1, o R2 foi atualizado com o novo catalogo.db
        obj_final_r2 = mock_s3.get_object(Bucket="aresta", Key="v1/catalogo.db")
        assert obj_final_r2["Body"].read() == b"sqlite-new-local"


def test_delta_deploy_falha_d1_aborta_antes_de_alterar_r2(deployer: Deployer, mock_s3) -> None:
    remoto_arquivos = {"indice.binarypb": "hash_old", "catalogo.db": "hash_cat_old"}
    mock_s3.put_object(
        Bucket="aresta",
        Key="v1/arquivos_serving.yaml",
        Body=criar_manifesto(remoto_arquivos).encode("utf-8"),
    )
    mock_s3.put_object(
        Bucket="aresta",
        Key="v1/catalogo.db",
        Body=b"sqlite-old-from-r2",
    )

    local_arquivos = {"indice.binarypb": "hash_new", "catalogo.db": "hash_cat_new"}
    (deployer.generated_dir / "arquivos_serving.yaml").write_bytes(
        criar_manifesto(local_arquivos).encode("utf-8")
    )
    (deployer.generated_dir / "indice.binarypb").write_bytes(b"new1")
    (deployer.generated_dir / "catalogo.db").write_bytes(b"sqlite-new-local")

    with (
        patch("subprocess.run"),
        patch(
            "serving.update_serving.sincronizar_catalogo_d1",
            side_effect=RuntimeError("Falha no D1"),
        ),
    ):
        with pytest.raises(RuntimeError, match="Falha no D1"):
            deployer.execute()

    # R2 permanece intacto com o catalogo.db antigo
    obj_r2 = mock_s3.get_object(Bucket="aresta", Key="v1/catalogo.db")
    assert obj_r2["Body"].read() == b"sqlite-old-from-r2"


def test_sincronizar_catalogo_d1_erro_s3_inesperado(deployer: Deployer) -> None:
    (deployer.generated_dir / "catalogo.db").write_bytes(b"sqlite-local")
    deployer.s3 = MagicMock()
    deployer.s3.get_object.side_effect = ClientError(
        {"Error": {"Code": "InternalError", "Message": "S3 error"}}, "GetObject"
    )
    with pytest.raises(ClientError):
        deployer._sincronizar_catalogo_d1()


def test_delta_deploy_no_changes(deployer: Deployer, capsys, mock_s3) -> None:
    arquivos = {"indice.binarypb": "same", "compilado.binarypb": "same"}
    data = criar_manifesto(arquivos).encode("utf-8")
    mock_s3.put_object(Bucket="aresta", Key="v1/arquivos_serving.yaml", Body=data)
    (deployer.generated_dir / "arquivos_serving.yaml").write_bytes(data)

    with patch("subprocess.run"):
        deployer.execute()

    out, _ = capsys.readouterr()
    assert "Nenhum arquivo modificado. Deploy pulado." in out


def test_delta_deploy_with_compilado_only(deployer: Deployer, mock_s3) -> None:
    remoto = {"indice.binarypb": "same", "catalogo.db": "same", "compilado.binarypb": "old"}
    mock_s3.put_object(
        Bucket="aresta",
        Key="v1/arquivos_serving.yaml",
        Body=criar_manifesto(remoto).encode("utf-8"),
    )

    local = {"indice.binarypb": "same", "catalogo.db": "same", "compilado.binarypb": "new"}
    (deployer.generated_dir / "arquivos_serving.yaml").write_text(
        criar_manifesto(local), encoding="utf-8"
    )
    (deployer.generated_dir / "compilado.binarypb").write_bytes(b"content")

    with (
        patch("subprocess.run") as mock_run,
        patch.object(deployer.purger, "purge_manifests"),
    ):
        deployer.execute()
        mock_run.assert_any_call(
            [
                "git",
                "checkout",
                "HEAD",
                "--ignore-skip-worktree-bits",
                "--",
                "generated/arquivos_serving.yaml",
                "generated/catalogo.db",
                "generated/compilado.binarypb",
                "generated/indice.binarypb",
            ],
            check=True,
        )


def test_upload_file_content_types_e_operacoes_vazias(deployer: Deployer, mock_s3) -> None:
    arquivos_teste = {
        "doc.pdf": "application/pdf",
        "imagem.webp": "image/webp",
        "foto.jpg": "image/jpeg",
        "icone.png": "image/png",
        "texto.md": "text/markdown; charset=utf-8",
        "config.yaml": "text/yaml; charset=utf-8",
        "binario.bin": "application/octet-stream",
    }
    for nome in arquivos_teste:
        (deployer.generated_dir / nome).write_bytes(b"dados")
        deployer._upload_file(nome)

    for nome, content_type in arquivos_teste.items():
        obj = mock_s3.get_object(Bucket="aresta", Key=f"v1/{nome}")
        assert obj["ContentType"] == content_type

    # Listas vazias não devem falhar
    deployer._upload_files_parallel([])
    deployer._delete_files_bulk([])


def test_deploy_envia_arquivos_em_tres_estagios_sequenciais_midias_compilados_manifestos(
    deployer: Deployer, mock_s3
) -> None:
    """Garante que mídias cheguem ao R2 antes de compilado.binarypb, e compilado.binarypb antes dos manifestos."""
    local_arquivos = {
        "arquivos_serving.yaml": "hash_manifest",
        "catalogo.db": "hash_cat",
        "indice.binarypb": "hash_ind_bin",
        "indice.yaml": "hash_ind_yaml",
        "alfa_pico/compilado.binarypb": "hash_comp_alfa",
        "zed_pico/compilado.binarypb": "hash_comp_zed",
        "zed_pico/imagens/topo.webp": "hash_midia_topo",
        "thumbnails/zed_pico.webp": "hash_thumb",
    }

    for rel_path in local_arquivos:
        caminho = deployer.generated_dir / rel_path
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(f"conteudo:{rel_path}".encode("utf-8"))

    (deployer.generated_dir / "arquivos_serving.yaml").write_bytes(
        criar_manifesto(local_arquivos).encode("utf-8")
    )

    upload_original = mock_s3.upload_file
    ordem_chaves_enviadas: list[str] = []

    def _rastrear_upload(Filename: str, Bucket: str, Key: str, ExtraArgs=None) -> None:
        ordem_chaves_enviadas.append(Key)
        upload_original(Filename, Bucket, Key, ExtraArgs=ExtraArgs)

    with (
        patch("subprocess.run"),
        patch("serving.update_serving.sincronizar_catalogo_d1"),
        patch.object(mock_s3, "upload_file", side_effect=_rastrear_upload),
        patch.object(deployer.purger, "purge_manifests") as mock_purge,
    ):
        deployer.execute()
        mock_purge.assert_called_once_with("v1")

    chaves_midia = {
        "v1/zed_pico/imagens/topo.webp",
        "v1/thumbnails/zed_pico.webp",
    }
    chaves_compilados = {
        "v1/alfa_pico/compilado.binarypb",
        "v1/zed_pico/compilado.binarypb",
    }
    chaves_manifestos = {
        "v1/arquivos_serving.yaml",
        "v1/catalogo.db",
        "v1/indice.binarypb",
        "v1/indice.yaml",
    }

    indices_midia = [ordem_chaves_enviadas.index(k) for k in chaves_midia]
    indices_compilados = [ordem_chaves_enviadas.index(k) for k in chaves_compilados]
    indices_manifestos = [ordem_chaves_enviadas.index(k) for k in chaves_manifestos]

    assert max(indices_midia) < min(indices_compilados), (
        f"Todas as mídias devem terminar antes do 1º compilado.binarypb. Ordem: {ordem_chaves_enviadas}"
    )
    assert max(indices_compilados) < min(indices_manifestos), (
        f"Todos os compilado.binarypb devem terminar antes do 1º manifesto raiz. Ordem: {ordem_chaves_enviadas}"
    )

    # Verifica também o caminho de Delta Deploy quando todos os arquivos sofrem atualização
    ordem_chaves_enviadas.clear()
    delta_arquivos = {k: f"{v}_v2" for k, v in local_arquivos.items()}
    (deployer.generated_dir / "arquivos_serving.yaml").write_bytes(
        criar_manifesto(delta_arquivos).encode("utf-8")
    )

    with (
        patch("subprocess.run"),
        patch("serving.update_serving.sincronizar_catalogo_d1"),
        patch.object(mock_s3, "upload_file", side_effect=_rastrear_upload),
        patch.object(deployer.purger, "purge_manifests") as mock_purge_delta,
    ):
        deployer.execute()
        mock_purge_delta.assert_called_once_with("v1")

    indices_midia_delta = [ordem_chaves_enviadas.index(k) for k in chaves_midia]
    indices_compilados_delta = [ordem_chaves_enviadas.index(k) for k in chaves_compilados]
    indices_manifestos_delta = [ordem_chaves_enviadas.index(k) for k in chaves_manifestos]

    assert max(indices_midia_delta) < min(indices_compilados_delta)
    assert max(indices_compilados_delta) < min(indices_manifestos_delta)


