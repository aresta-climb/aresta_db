# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import base64
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from editor.release_tools.publicar_beta_cli import main as cli_main


def test_publicar_beta_cli_sucesso(tmp_path: Path) -> None:
    """Valida a execução do utilitário CLI de publicação do canal Beta."""
    msix = tmp_path / "EditorArestaBeta.msix"
    msix.write_bytes(b"MSIX_TESTE")

    cer = tmp_path / "teste.cer"
    cer.write_bytes(b"DADOS_CERT_DER_FALSOS")

    mock_publicador = MagicMock()
    mock_publicador.publicar_e_purgar.return_value = True

    with patch("editor.release_tools.publicar_beta_cli.PublicadorR2Beta", return_value=mock_publicador):
        codigo_saida = cli_main([
            "--versao", "0.2.1",
            "--msix", str(msix),
            "--cer", str(cer),
            "--diretorio-saida", str(tmp_path),
        ])

        assert codigo_saida == 0
        assert (tmp_path / "EditorAresta.appinstaller").exists()
        assert (tmp_path / "InstalarCertificadoEditorArestaBeta.bat").exists()
        mock_publicador.publicar_e_purgar.assert_called_once()


def test_publicar_beta_cli_com_cer_pem_existente(tmp_path: Path) -> None:
    """Valida a extração quando o arquivo de certificado já está em formato PEM."""
    msix = tmp_path / "EditorArestaBeta.msix"
    msix.write_bytes(b"MSIX_TESTE")

    cer = tmp_path / "teste_pem.cer"
    cer.write_text("-----BEGIN CERTIFICATE-----\nMIIB_DADOS\n-----END CERTIFICATE-----", encoding="utf-8")

    mock_publicador = MagicMock()
    mock_publicador.publicar_e_purgar.return_value = True

    with patch("editor.release_tools.publicar_beta_cli.PublicadorR2Beta", return_value=mock_publicador):
        codigo = cli_main([
            "--versao", "0.2.1",
            "--msix", str(msix),
            "--cer", str(cer),
            "--diretorio-saida", str(tmp_path),
        ])
        assert codigo == 0
        conteudo_bat = (tmp_path / "InstalarCertificadoEditorArestaBeta.bat").read_text(encoding="utf-8")
        assert "MIIB_DADOS" in conteudo_bat


def test_publicar_beta_cli_com_bytes_der_nao_utf8(tmp_path: Path) -> None:
    """Valida a conversão de bytes binários DER não decodificáveis como UTF-8."""
    msix = tmp_path / "EditorArestaBeta.msix"
    msix.write_bytes(b"MSIX_TESTE")

    cer = tmp_path / "teste_bin.cer"
    cer.write_bytes(b"\xff\xfe\x00\x12\x34\x56\x78\x90")

    mock_publicador = MagicMock()
    mock_publicador.publicar_e_purgar.return_value = True

    with patch("editor.release_tools.publicar_beta_cli.PublicadorR2Beta", return_value=mock_publicador):
        codigo = cli_main([
            "--versao", "0.2.1",
            "--msix", str(msix),
            "--cer", str(cer),
            "--diretorio-saida", str(tmp_path),
        ])
        assert codigo == 0


def test_publicar_beta_cli_falha_publicacao_retorna_um(tmp_path: Path) -> None:
    """Valida se retorno falso do publicador resulta em código de saída 1."""
    msix = tmp_path / "EditorArestaBeta.msix"
    msix.write_bytes(b"MSIX_TESTE")

    mock_publicador = MagicMock()
    mock_publicador.publicar_e_purgar.return_value = False

    with patch("editor.release_tools.publicar_beta_cli.PublicadorR2Beta", return_value=mock_publicador):
        codigo = cli_main([
            "--versao", "0.2.1",
            "--msix", str(msix),
            "--diretorio-saida", str(tmp_path),
        ])
        assert codigo == 1


def test_publicar_beta_cli_falha_sem_msix(tmp_path: Path) -> None:
    """Garante que a ausência do arquivo MSIX resulte em código de erro diferente de zero."""
    with pytest.raises(FileNotFoundError):
        cli_main([
            "--versao", "0.2.1",
            "--msix", str(tmp_path / "inexistente.msix"),
        ])


def test_publicar_beta_cli_execucao_modulo() -> None:
    """Valida a execução do ponto de entrada __main__ via runpy."""
    import runpy
    with patch.object(sys, "argv", ["publicar_beta_cli.py", "--help"]):
        with pytest.raises(SystemExit) as exit_info:
            runpy.run_module("editor.release_tools.publicar_beta_cli", run_name="__main__")
        assert exit_info.value.code == 0
