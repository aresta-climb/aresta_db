# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para a biblioteca de publicação do Flatpak OSTree no Cloudflare R2
(editor.release_tools.publicar_flatpak_r2).
"""

import configparser
import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from editor.release_tools.publicar_flatpak_r2 import (
    PublicadorFlatpakR2,
    determinar_tipo_conteudo_flatpak,
    gerar_conteudo_flatpakref,
    gerar_conteudo_flatpakrepo,
    gerar_conteudo_version_json,
    verificar_estado_repositorio_remoto,
)


def test_verificar_estado_repositorio_remoto_existe_retorna_true() -> None:
    """Quando o summary remoto responder HTTP 200, retorna True (repositório existente)."""
    mock_resposta = MagicMock()
    mock_resposta.__enter__.return_value.status = 200

    with patch("urllib.request.urlopen", return_value=mock_resposta):
        assert (
            verificar_estado_repositorio_remoto(
                "https://serving.arestaclimb.com/flatpak/repo/summary"
            )
            is True
        )


def test_verificar_estado_repositorio_remoto_novo_retorna_false() -> None:
    """Quando o summary remoto responder HTTP 404, retorna False (repositório novo / bootstrap)."""
    erro_404 = urllib.error.HTTPError(
        url="https://serving.arestaclimb.com/flatpak/repo/summary",
        code=404,
        msg="Not Found",
        hdrs=MagicMock(),
        fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=erro_404):
        assert (
            verificar_estado_repositorio_remoto(
                "https://serving.arestaclimb.com/flatpak/repo/summary"
            )
            is False
        )


def test_verificar_estado_repositorio_remoto_erro_servidor_levanta_excecao() -> None:
    """Quando o summary responder status de erro diferente de 404, levanta RuntimeError sem mascarar com || true."""
    erro_500 = urllib.error.HTTPError(
        url="https://serving.arestaclimb.com/flatpak/repo/summary",
        code=500,
        msg="Internal Server Error",
        hdrs=MagicMock(),
        fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=erro_500):
        with pytest.raises(RuntimeError, match="Falha ao checar repositório remoto.*500"):
            verificar_estado_repositorio_remoto(
                "https://serving.arestaclimb.com/flatpak/repo/summary"
            )


def test_verificar_estado_repositorio_remoto_erro_rede_levanta_excecao() -> None:
    """Falha de conexão / DNS / socket levanta RuntimeError explícito."""
    erro_url = urllib.error.URLError(reason="Connection refused")
    with patch("urllib.request.urlopen", side_effect=erro_url):
        with pytest.raises(RuntimeError, match="Erro de rede ao verificar repositório remoto"):
            verificar_estado_repositorio_remoto(
                "https://serving.arestaclimb.com/flatpak/repo/summary"
            )


def test_gerar_conteudo_version_json() -> None:
    """Gera JSON válido com versao, obrigatoria, mensagem opcional e timestamp ISO."""
    conteudo = gerar_conteudo_version_json(
        "0.5.0", obrigatoria=True, mensagem="Atualização crítica"
    )
    dados = json.loads(conteudo)
    assert dados["versao"] == "0.5.0"
    assert dados["obrigatoria"] is True
    assert dados["mensagem"] == "Atualização crítica"
    assert "timestamp" in dados


def test_gerar_conteudo_flatpakref() -> None:
    """Gera arquivo .flatpakref estruturado no padrão INI do Flatpak."""
    conteudo = gerar_conteudo_flatpakref(
        nome_app="com.arestaclimb.Editor",
        branch="stable",
        titulo="Editor Aresta",
        url_repo="https://serving.arestaclimb.com/flatpak/repo",
        chave_gpg_base64="MOCK_GPG_BASE64",
    )
    parser = configparser.ConfigParser()
    parser.read_string(conteudo)
    assert parser.has_section("Flatpak Ref")
    assert parser.get("Flatpak Ref", "Name") == "com.arestaclimb.Editor"
    assert parser.get("Flatpak Ref", "Branch") == "stable"
    assert parser.get("Flatpak Ref", "Title") == "Editor Aresta"
    assert parser.get("Flatpak Ref", "Url") == "https://serving.arestaclimb.com/flatpak/repo"
    assert parser.get("Flatpak Ref", "IsRuntime") == "false"
    assert parser.get("Flatpak Ref", "GPGKey") == "MOCK_GPG_BASE64"
    assert "flathub" in parser.get("Flatpak Ref", "RuntimeRepo")


def test_gerar_conteudo_flatpakrepo() -> None:
    """Gera arquivo .flatpakrepo no formato padrão aceito pelo flatpak remote-add."""
    conteudo = gerar_conteudo_flatpakrepo(
        titulo="Aresta Climb",
        url_repo="https://serving.arestaclimb.com/flatpak/repo",
        homepage="https://arestaclimb.com",
        comentario="Repositório oficial",
        descricao="Repositório do Editor",
        url_icone="https://serving.arestaclimb.com/flatpak/logo.png",
        chave_gpg_base64="MOCK_GPG_BASE64",
    )
    parser = configparser.ConfigParser()
    parser.read_string(conteudo)
    assert parser.has_section("Flatpak Repo")
    assert parser.get("Flatpak Repo", "Title") == "Aresta Climb"
    assert parser.get("Flatpak Repo", "Url") == "https://serving.arestaclimb.com/flatpak/repo"
    assert parser.get("Flatpak Repo", "GPGKey") == "MOCK_GPG_BASE64"
    assert parser.get("Flatpak Repo", "Icon") == "https://serving.arestaclimb.com/flatpak/logo.png"


def test_determinar_tipo_conteudo_flatpak() -> None:
    """Determina corretamente o Content-Type para artefatos do repositório OSTree e metadados."""
    assert determinar_tipo_conteudo_flatpak(Path("version.json")) == "application/json"
    assert (
        determinar_tipo_conteudo_flatpak(Path("com.arestaclimb.Editor.flatpakref"))
        == "text/plain; charset=utf-8"
    )
    assert (
        determinar_tipo_conteudo_flatpak(Path("aresta.flatpakrepo")) == "text/plain; charset=utf-8"
    )
    assert determinar_tipo_conteudo_flatpak(Path("logo.png")) == "image/png"
    assert determinar_tipo_conteudo_flatpak(Path("summary")) == "application/octet-stream"
    assert determinar_tipo_conteudo_flatpak(Path("summary.sig")) == "application/octet-stream"
    assert (
        determinar_tipo_conteudo_flatpak(Path("objects/ab/1234.filez"))
        == "application/octet-stream"
    )


def test_publicador_flatpak_r2_inicializacao_cliente_s3() -> None:
    """Testa inicialização do cliente S3 a partir das variáveis de ambiente."""
    env = {
        "CLOUDFLARE_S3_API_URL": "https://fake.r2.cloudflarestorage.com",
        "AWS_ACCESS_KEY_ID": "fake_key",
        "AWS_SECRET_ACCESS_KEY": "fake_secret",
        "CLOUDFLARE_ZONE_ID": "fake_zone",
        "CLOUDFLARE_CACHE_PURGE_API_TOKEN": "fake_token",
    }
    with patch.dict("os.environ", env, clear=True):
        with patch("boto3.client") as mock_boto:
            publicador = PublicadorFlatpakR2()
            cliente = publicador.cliente_s3
            assert cliente is not None
            mock_boto.assert_called_once()
            args, kwargs = mock_boto.call_args
            assert args[0] == "s3"
            assert kwargs["endpoint_url"] == "https://fake.r2.cloudflarestorage.com"
            assert kwargs["aws_access_key_id"] == "fake_key"
            assert kwargs["aws_secret_access_key"] == "fake_secret"


def test_publicador_flatpak_r2_sincronizar_diretorio_ostree(tmp_path: Path) -> None:
    """Testa sincronização incremental de arquivos do repositório local com o bucket R2."""
    diretorio_repo = tmp_path / "repo"
    diretorio_repo.mkdir()

    # Cria arquivos de teste
    (diretorio_repo / "config").write_text("[core]\nmode=archive-z2\n", encoding="utf-8")
    (diretorio_repo / "summary").write_bytes(b"mock_summary_data")
    pasta_objects = diretorio_repo / "objects" / "ab"
    pasta_objects.mkdir(parents=True)
    obj_novo = pasta_objects / "novo.filez"
    obj_novo.write_bytes(b"dados_novos")
    obj_existente = pasta_objects / "existente.filez"
    obj_existente.write_bytes(b"dados_existentes")

    mock_s3 = MagicMock()

    # Simula que 'existente.filez' já existe no bucket
    def mock_head_object(Bucket: str, Key: str) -> dict[str, str]:
        if "existente.filez" in Key:
            return {"ContentLength": "16"}
        from botocore.exceptions import ClientError

        raise ClientError({"Error": {"Code": "404"}}, "head_object")

    mock_s3.head_object.side_effect = mock_head_object

    publicador = PublicadorFlatpakR2(cliente_s3=mock_s3)
    chaves_enviadas = publicador.sincronizar_diretorio_ostree(diretorio_repo)

    assert "flatpak/repo/config" in chaves_enviadas
    assert "flatpak/repo/summary" in chaves_enviadas
    assert "flatpak/repo/objects/ab/novo.filez" in chaves_enviadas
    assert "flatpak/repo/objects/ab/existente.filez" not in chaves_enviadas

    # Valida que todos os uploads usam cabeçalho CacheControl uniforme
    for call in mock_s3.upload_file.call_args_list:
        extra_args = call[1].get("ExtraArgs", {})
        assert extra_args.get("CacheControl") == "public, max-age=31536000, immutable"


def test_publicador_flatpak_r2_sincronizar_diretorio_inexistente() -> None:
    """Sincronizar diretório inexistente levanta FileNotFoundError."""
    publicador = PublicadorFlatpakR2(cliente_s3=MagicMock())
    with pytest.raises(FileNotFoundError):
        publicador.sincronizar_diretorio_ostree(Path("/caminho/nao/existe"))


def test_publicador_flatpak_r2_publicar_metadados(tmp_path: Path) -> None:
    """Testa geração local e envio para o R2 dos metadados (version.json, .flatpakref, .flatpakrepo)."""
    mock_s3 = MagicMock()
    publicador = PublicadorFlatpakR2(cliente_s3=mock_s3)

    arquivos = publicador.publicar_metadados(
        versao="0.5.0",
        chave_gpg_base64="MOCK_GPG",
        diretorio_saida=tmp_path,
        obrigatoria=True,
    )

    assert "version.json" in arquivos
    assert "com.arestaclimb.Editor.flatpakref" in arquivos
    assert "aresta.flatpakrepo" in arquivos

    for path in arquivos.values():
        assert path.exists()

    assert mock_s3.upload_file.call_count == 3


def test_publicador_flatpak_r2_purgar_cache_sucesso() -> None:
    """Testa chamada com sucesso à API de purgação da Cloudflare."""
    mock_resposta = MagicMock()
    mock_resposta.__enter__.return_value.status = 200

    publicador = PublicadorFlatpakR2(zone_id="fake_zone", api_token="fake_token")
    with patch("urllib.request.urlopen", return_value=mock_resposta) as mock_urlopen:
        sucesso = publicador.purgar_cache(["https://serving.arestaclimb.com/flatpak/version.json"])
        assert sucesso is True
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Authorization") == "Bearer fake_token"
        assert req.get_header("Content-type") == "application/json"
        corpo = json.loads(req.data.decode("utf-8"))
        assert corpo["files"] == ["https://serving.arestaclimb.com/flatpak/version.json"]


def test_publicador_flatpak_r2_purgar_cache_credenciais_ausentes() -> None:
    """Tentativa de purgar sem zone_id ou api_token levanta ValueError."""
    publicador = PublicadorFlatpakR2(zone_id=None, api_token=None)
    with pytest.raises(ValueError, match="Credenciais da Cloudflare ausentes"):
        publicador.purgar_cache(["https://fake.url"])


def test_publicador_flatpak_r2_purgar_cache_erro_http() -> None:
    """Erro HTTP na API da Cloudflare levanta RuntimeError com detalhes."""
    erro_http = urllib.error.HTTPError(
        url="https://api.cloudflare.com",
        code=403,
        msg="Forbidden",
        hdrs=MagicMock(),
        fp=None,
    )
    publicador = PublicadorFlatpakR2(zone_id="fake_zone", api_token="fake_token")
    with patch("urllib.request.urlopen", side_effect=erro_http):
        with pytest.raises(RuntimeError, match="Falha ao purgar cache do Cloudflare.*403"):
            publicador.purgar_cache(["https://fake.url"])


def test_publicador_flatpak_r2_obter_urls_purga() -> None:
    """Verifica lista canônica de URLs mutáveis para purgação na Cloudflare."""
    publicador = PublicadorFlatpakR2(uri_base="https://serving.arestaclimb.com/flatpak")
    urls = publicador.obter_urls_purga()
    assert "https://serving.arestaclimb.com/flatpak/repo/summary" in urls
    assert "https://serving.arestaclimb.com/flatpak/repo/summary.sig" in urls
    assert "https://serving.arestaclimb.com/flatpak/version.json" in urls
    assert "https://serving.arestaclimb.com/flatpak/com.arestaclimb.Editor.flatpakref" in urls
    assert "https://serving.arestaclimb.com/flatpak/aresta.flatpakrepo" in urls
