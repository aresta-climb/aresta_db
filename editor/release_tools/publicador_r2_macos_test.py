# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o publicador de artefatos do canal macOS no Cloudflare R2.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from editor.release_tools.publicador_r2_macos import PublicadorR2MacOS


def test_publicador_r2_macos_inicializacao() -> None:
    """Valida a inicialização padrão e com parâmetros customizados."""
    pub_padrao = PublicadorR2MacOS()
    assert pub_padrao.bucket == "aresta-serving"
    assert pub_padrao.prefixo == "editor-macos"
    assert pub_padrao.uri_base == "https://serving.arestaclimb.com/editor-macos"

    pub_custom = PublicadorR2MacOS(
        bucket="meu-bucket",
        prefixo="meu-prefixo",
        uri_base="https://custom.com/mac/",
        zone_id="zona1",
        api_token="token1",
    )
    assert pub_custom.bucket == "meu-bucket"
    assert pub_custom.prefixo == "meu-prefixo"
    assert pub_custom.uri_base == "https://custom.com/mac"
    assert pub_custom.zone_id == "zona1"
    assert pub_custom.api_token == "token1"


def test_publicador_r2_macos_cliente_s3_property() -> None:
    """Valida inicialização preguiçosa de boto3 no property cliente_s3."""
    with patch.dict(
        "os.environ",
        {
            "CLOUDFLARE_S3_API_URL": "https://r2.exemplo.com",
            "AWS_ACCESS_KEY_ID": "ak_teste",
            "AWS_SECRET_ACCESS_KEY": "sk_teste",
        },
    ):
        mock_boto = MagicMock()
        with patch.dict("sys.modules", {"boto3": mock_boto}):
            pub = PublicadorR2MacOS()
            s3 = pub.cliente_s3
            assert s3 is not None
            mock_boto.client.assert_called_once_with(
                "s3",
                endpoint_url="https://r2.exemplo.com",
                aws_access_key_id="ak_teste",
                aws_secret_access_key="sk_teste",
                region_name="auto",
            )


def test_publicador_r2_macos_cliente_s3_account_id_fallback() -> None:
    """Valida montagem de endpoint URL com CLOUDFLARE_ACCOUNT_ID quando API_URL não for informada."""
    with patch.dict(
        "os.environ",
        {
            "CLOUDFLARE_ACCOUNT_ID": "acc123",
            "AWS_ACCESS_KEY_ID": "ak",
            "AWS_SECRET_ACCESS_KEY": "sk",
        },
        clear=True,
    ):
        mock_boto = MagicMock()
        with patch.dict("sys.modules", {"boto3": mock_boto}):
            pub = PublicadorR2MacOS()
            _ = pub.cliente_s3
            mock_boto.client.assert_called_once_with(
                "s3",
                endpoint_url="https://acc123.r2.cloudflarestorage.com",
                aws_access_key_id="ak",
                aws_secret_access_key="sk",
                region_name="auto",
            )


def test_publicar_artefatos_sucesso(tmp_path: Path) -> None:
    """Valida upload de DMG versionado, DMG latest e appcast.xml no bucket S3."""
    dmg = tmp_path / "EditorAresta-0.5.13.dmg"
    dmg.write_bytes(b"CONTEUDO_DMG")

    appcast = tmp_path / "appcast.xml"
    appcast.write_text("<xml/>", encoding="utf-8")

    mock_s3 = MagicMock()
    pub = PublicadorR2MacOS(cliente_s3=mock_s3)

    chaves = pub.publicar_artefatos(
        versao="0.5.13",
        caminho_dmg=dmg,
        caminho_appcast=appcast,
    )

    assert len(chaves) == 3
    assert "editor-macos/EditorAresta-0.5.13.dmg" in chaves
    assert "editor-macos/EditorAresta-latest.dmg" in chaves
    assert "editor-macos/appcast.xml" in chaves

    assert mock_s3.upload_file.call_count == 3


def test_publicar_artefatos_arquivos_inexistentes(tmp_path: Path) -> None:
    """Valida que arquivos inexistentes são ignorados sem erro."""
    mock_s3 = MagicMock()
    pub = PublicadorR2MacOS(cliente_s3=mock_s3)

    chaves = pub.publicar_artefatos(
        versao="0.5.13",
        caminho_dmg=tmp_path / "inexistente.dmg",
        caminho_appcast=tmp_path / "inexistente.xml",
    )

    assert chaves == []
    assert mock_s3.upload_file.call_count == 0


def test_purga_cache_cloudflare_sucesso() -> None:
    """Valida envio da requisição de purgação de cache para o Cloudflare."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    pub = PublicadorR2MacOS(
        zone_id="zona_abc",
        api_token="token_xyz",
    )

    with patch("requests.post", return_value=mock_resp) as mock_post:
        sucesso = pub.purga_cache_cloudflare(versao="0.5.13")
        assert sucesso is True
        mock_post.assert_called_once()
        chamada = mock_post.call_args
        assert "zones/zona_abc/purge_cache" in chamada[0][0]
        assert chamada[1]["headers"]["Authorization"] == "Bearer token_xyz"
        arquivos = chamada[1]["json"]["files"]
        assert "https://serving.arestaclimb.com/editor-macos/EditorAresta-0.5.13.dmg" in arquivos
        assert "https://serving.arestaclimb.com/editor-macos/EditorAresta-latest.dmg" in arquivos
        assert "https://serving.arestaclimb.com/editor-macos/appcast.xml" in arquivos


def test_purga_cache_cloudflare_sem_credenciais() -> None:
    """Valida que ausência de zone_id ou api_token pula a purgação retornando False."""
    pub = PublicadorR2MacOS(zone_id=None, api_token=None)
    assert pub.purga_cache_cloudflare(versao="0.5.13") is False


def test_purga_cache_cloudflare_trata_erros() -> None:
    """Valida tratamento seguro de RequestException na purgação de cache."""
    pub = PublicadorR2MacOS(zone_id="zona", api_token="tok")

    with patch("requests.post", side_effect=requests.RequestException("Falha de conexão")):
        assert pub.purga_cache_cloudflare(versao="0.5.13") is False


def test_purga_cache_cloudflare_status_diferente_200() -> None:
    """Valida quando a CDN Cloudflare retorna status diferente de 200 (ex: 202 ou 400)."""
    pub = PublicadorR2MacOS(zone_id="zona", api_token="tok")
    mock_resp = MagicMock()
    mock_resp.status_code = 202

    with patch("requests.post", return_value=mock_resp):
        assert pub.purga_cache_cloudflare(versao="0.5.13") is False


def test_publicar_e_purgar_fluxo_completo(tmp_path: Path) -> None:
    """Valida orquestração de upload e purgação com sucesso."""
    dmg = tmp_path / "EditorAresta-0.5.13.dmg"
    dmg.write_bytes(b"DMG")

    appcast = tmp_path / "appcast.xml"
    appcast.write_text("<xml/>", encoding="utf-8")

    mock_s3 = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    pub = PublicadorR2MacOS(
        cliente_s3=mock_s3,
        zone_id="zona",
        api_token="tok",
    )

    with patch("requests.post", return_value=mock_resp):
        sucesso = pub.publicar_e_purgar(
            versao="0.5.13",
            caminho_dmg=dmg,
            caminho_appcast=appcast,
        )
        assert sucesso is True
        assert mock_s3.upload_file.call_count == 3
