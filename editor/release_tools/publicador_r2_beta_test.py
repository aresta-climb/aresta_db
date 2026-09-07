# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from editor.release_tools.publicador_r2_beta import (
    PublicadorR2Beta,
    determinar_tipo_conteudo,
)


def test_determinar_tipo_conteudo() -> None:
    """Verifica se os tipos MIME corretos são atribuídos aos artefatos do canal Beta."""
    assert determinar_tipo_conteudo(Path("EditorAresta.appinstaller")) == "application/appinstaller"
    assert determinar_tipo_conteudo(Path("EditorArestaBeta.msix")) == "application/msix"
    assert determinar_tipo_conteudo(Path("InstalarCertificado.bat")) == "application/x-bat"
    assert determinar_tipo_conteudo(Path("outro.bin")) == "application/octet-stream"


def test_publicador_r2_beta_sucesso(tmp_path: Path) -> None:
    """Valida o fluxo completo de upload e purgação com sucesso."""
    appinstaller = tmp_path / "EditorAresta.appinstaller"
    appinstaller.write_text("<AppInstaller />", encoding="utf-8")

    msix = tmp_path / "EditorArestaBeta.msix"
    msix.write_bytes(b"MSIX_DADOS")

    bat = tmp_path / "InstalarCertificadoEditorArestaBeta.bat"
    bat.write_text("@echo off", encoding="utf-8")

    mock_s3 = MagicMock()
    mock_resp_purge = MagicMock()
    mock_resp_purge.__enter__.return_value.status = 200

    publicador = PublicadorR2Beta(
        cliente_s3=mock_s3,
        bucket="aresta-serving",
        zone_id="zona_teste",
        api_token="token_teste",
        uri_base="https://serving.arestaclimb.com/editor-beta",
    )

    with patch("urllib.request.urlopen", return_value=mock_resp_purge) as mock_urlopen:
        sucesso = publicador.publicar_e_purgar(appinstaller, msix, bat)
        assert sucesso is True

        assert mock_s3.upload_file.call_count == 3
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        corpo = json.loads(req.data.decode("utf-8"))
        assert "https://serving.arestaclimb.com/editor-beta/EditorAresta.appinstaller" in corpo["files"]
        assert "https://serving.arestaclimb.com/editor-beta/EditorArestaBeta.msix" in corpo["files"]


def test_publicador_r2_beta_arquivo_inexistente(tmp_path: Path) -> None:
    """Garante que a tentativa de upload de arquivo inexistente levante FileNotFoundError."""
    publicador = PublicadorR2Beta(
        cliente_s3=MagicMock(),
        bucket="aresta-serving",
        zone_id="zona_teste",
        api_token="token_teste",
    )

    with pytest.raises(FileNotFoundError, match="Arquivo local não encontrado"):
        publicador.enviar_arquivo(tmp_path / "nao_existe.msix", "editor-beta/nao_existe.msix")


def test_publicador_r2_beta_falha_purge_lanca_excecao(tmp_path: Path) -> None:
    """Valida se erros HTTP da API Cloudflare levantam exceção descritiva."""
    appinstaller = tmp_path / "EditorAresta.appinstaller"
    appinstaller.write_text("<AppInstaller />", encoding="utf-8")

    msix = tmp_path / "EditorArestaBeta.msix"
    msix.write_bytes(b"MSIX_DADOS")

    mock_s3 = MagicMock()
    publicador = PublicadorR2Beta(
        cliente_s3=mock_s3,
        bucket="aresta-serving",
        zone_id="zona_teste",
        api_token="token_teste",
    )

    erro_http = urllib.error.HTTPError(
        url="https://api.cloudflare.com",
        code=403,
        msg="Forbidden",
        hdrs=MagicMock(),
        fp=MagicMock(),
    )

    with patch("urllib.request.urlopen", side_effect=erro_http):
        with pytest.raises(RuntimeError, match="Falha ao purgar cache do Cloudflare"):
            publicador.publicar_e_purgar(appinstaller, msix)


def test_publicador_r2_beta_inicializacao_preguicosa_s3() -> None:
    """Garante que a propriedade cliente_s3 instancia o cliente boto3 se não injetado."""
    with patch("boto3.client") as mock_boto:
        publicador = PublicadorR2Beta(cliente_s3=None)
        cliente = publicador.cliente_s3
        assert cliente == mock_boto.return_value


def test_publicador_r2_beta_purgar_sem_credenciais() -> None:
    """Garante que a tentativa de purgação sem zone_id ou api_token lance ValueError."""
    with patch.dict("os.environ", {}, clear=True):
        publicador = PublicadorR2Beta(cliente_s3=MagicMock(), zone_id=None, api_token=None)
        with pytest.raises(ValueError, match="Credenciais da Cloudflare ausentes"):
            publicador.purgar_cache(["https://serving.arestaclimb.com/teste"])
