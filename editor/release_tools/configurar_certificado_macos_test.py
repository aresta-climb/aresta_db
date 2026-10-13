# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o módulo de configuração de certificados Apple Developer ID no macOS.
"""

import base64
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from editor.release_tools.configurar_certificado_macos import (
    configurar_keychain_e_certificado_macos,
    converter_pkcs12_para_formato_compativel_macos,
    decodificar_certificado_base64,
    importar_certificado_na_keychain,
    main,
)


class TestConfigurarCertificadoMacOS(unittest.TestCase):
    def setUp(self) -> None:
        self.diretorio_temporario = tempfile.TemporaryDirectory()
        self.pasta_temp = Path(self.diretorio_temporario.name)

    def tearDown(self) -> None:
        self.diretorio_temporario.cleanup()

    def test_decodificar_certificado_base64_sucesso(self) -> None:
        """Garante decodificação de base64 mesmo com quebras de linha e espaços."""
        conteudo_original = b"CONTEUDO_BINARIO_DO_CERTIFICADO_P12"
        b64_com_quebras = "\n  " + base64.b64encode(conteudo_original).decode("ascii") + "\n\n"

        destino = self.pasta_temp / "cert.p12"
        resultado = decodificar_certificado_base64(b64_com_quebras, destino)

        self.assertEqual(resultado, destino)
        self.assertTrue(destino.exists())
        self.assertEqual(destino.read_bytes(), conteudo_original)

    def test_decodificar_certificado_base64_invalido_lanca_excecao(self) -> None:
        """Valida que base64 corrompido ou inválido lança ValueError informativo."""
        destino = self.pasta_temp / "cert_invalido.p12"
        with self.assertRaises(ValueError):
            decodificar_certificado_base64("###_NAO_EH_BASE64_VALIDO_###", destino)

    def test_converter_pkcs12_executa_openssl_com_flags_legacy(self) -> None:
        """Garante que a conversão utiliza openssl para exportar com cifras compatíveis com o Keychain."""
        caminho_p12 = self.pasta_temp / "original.p12"
        caminho_p12.write_bytes(b"p12_original")
        destino = self.pasta_temp / "compat.p12"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            resultado = converter_pkcs12_para_formato_compativel_macos(
                caminho_p12=caminho_p12,
                senha="senha-segura-123",
                destino=destino,
            )

            self.assertEqual(resultado, destino)
            self.assertEqual(mock_run.call_count, 2)
            # Primeira chamada: extrair para PEM
            args_extrair = mock_run.call_args_list[0][0][0]
            self.assertIn("openssl", args_extrair)
            self.assertIn("pkcs12", args_extrair)
            self.assertIn("-nodes", args_extrair)
            self.assertIn("pass:senha-segura-123", args_extrair)

            # Segunda chamada: reexportar com legacy
            args_exportar = mock_run.call_args_list[1][0][0]
            self.assertIn("openssl", args_exportar)
            self.assertIn("-legacy", args_exportar)
            self.assertIn("pass:senha-segura-123", args_exportar)

    def test_converter_pkcs12_fallback_se_openssl_falhar_com_legacy(self) -> None:
        """Valida fallback gracioso caso a versão do OpenSSL (ex: LibreSSL) não suporte a flag -legacy."""
        caminho_p12 = self.pasta_temp / "original.p12"
        caminho_p12.write_bytes(b"p12_original")
        destino = self.pasta_temp / "compat.p12"

        with patch("subprocess.run") as mock_run:
            # 1ª chamada (extrair): ok
            # 2ª chamada (exportar -legacy): falha com erro de opção desconhecida
            # 3ª chamada (exportar sem -legacy): ok
            mock_run.side_effect = [
                MagicMock(returncode=0),
                subprocess.CalledProcessError(
                    1, ["openssl", "-legacy"], stderr=b"unknown option -legacy"
                ),
                MagicMock(returncode=0),
            ]

            resultado = converter_pkcs12_para_formato_compativel_macos(
                caminho_p12=caminho_p12,
                senha="senha",
                destino=destino,
            )

            self.assertEqual(resultado, destino)
            self.assertEqual(mock_run.call_count, 3)
            args_terceira = mock_run.call_args_list[2][0][0]
            self.assertNotIn("-legacy", args_terceira)

    def test_converter_pkcs12_retorna_original_se_openssl_nao_encontrado(self) -> None:
        """Garante que se o binário openssl não estiver presente, retorna o arquivo original."""
        caminho_p12 = self.pasta_temp / "original.p12"
        caminho_p12.write_bytes(b"p12_original")

        with patch("subprocess.run", side_effect=FileNotFoundError("openssl não encontrado")):
            resultado = converter_pkcs12_para_formato_compativel_macos(
                caminho_p12=caminho_p12,
                senha="senha",
            )
            self.assertEqual(resultado, caminho_p12)

    def test_importar_certificado_na_keychain_executa_sequencia_security(self) -> None:
        """Garante que a sequência exata de comandos security é executada com parâmetros seguros."""
        caminho_p12 = self.pasta_temp / "cert.p12"
        caminho_p12.write_bytes(b"cert_bytes")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            importar_certificado_na_keychain(
                caminho_p12=caminho_p12,
                senha_certificado="senha-cert",
                nome_keychain="build.keychain",
                senha_keychain="actions",
            )

            chamadas_comandos = [call_args[0][0] for call_args in mock_run.call_args_list]

            # 1. create-keychain
            self.assertTrue(
                any(c[:2] == ["security", "create-keychain"] for c in chamadas_comandos)
            )
            # 2. default-keychain
            self.assertTrue(
                any(c[:2] == ["security", "default-keychain"] for c in chamadas_comandos)
            )
            # 3. unlock-keychain
            self.assertTrue(
                any(c[:2] == ["security", "unlock-keychain"] for c in chamadas_comandos)
            )
            # 4. set-keychain-settings
            self.assertTrue(
                any(c[:2] == ["security", "set-keychain-settings"] for c in chamadas_comandos)
            )
            # 5. import
            import_cmd = next(c for c in chamadas_comandos if c[:2] == ["security", "import"])
            self.assertIn("-k", import_cmd)
            self.assertIn("build.keychain", import_cmd)
            self.assertIn("-P", import_cmd)
            self.assertIn("senha-cert", import_cmd)
            self.assertIn("-A", import_cmd)
            self.assertIn("-T", import_cmd)
            self.assertIn("/usr/bin/codesign", import_cmd)
            # 6. set-key-partition-list
            part_cmd = next(
                c for c in chamadas_comandos if c[:2] == ["security", "set-key-partition-list"]
            )
            self.assertIn("apple-tool:,apple:,codesign:", part_cmd)

    def test_configurar_keychain_e_certificado_macos_pula_se_sem_certificado(self) -> None:
        """Valida que a função orquestradora retorna False graciosamente se APPLE_CERT_P12 estiver vazio."""
        with patch.dict(os.environ, {"APPLE_CERT_P12": "", "APPLE_CERT_PASSWORD": ""}):
            resultado = configurar_keychain_e_certificado_macos()
            self.assertFalse(resultado)

    def test_configurar_keychain_e_certificado_macos_fluxo_completo_sucesso(self) -> None:
        """Valida fluxo orquestrador completo decodificando, convertendo e importando."""
        conteudo_b64 = base64.b64encode(b"MOCK_P12_CONTENT").decode("ascii")

        with (
            patch.dict(
                os.environ, {"APPLE_CERT_P12": conteudo_b64, "APPLE_CERT_PASSWORD": "secret-pass"}
            ),
            patch(
                "editor.release_tools.configurar_certificado_macos.converter_pkcs12_para_formato_compativel_macos"
            ) as mock_converter,
            patch(
                "editor.release_tools.configurar_certificado_macos.importar_certificado_na_keychain"
            ) as mock_importar,
        ):
            mock_converter.side_effect = lambda caminho_p12, senha, destino=None: (
                destino or caminho_p12
            )

            sucesso = configurar_keychain_e_certificado_macos(diretorio_trabalho=self.pasta_temp)

            self.assertTrue(sucesso)
            mock_converter.assert_called_once()
            mock_importar.assert_called_once()

    def test_main_executa_e_retorna_zero_quando_configurado(self) -> None:
        """Valida ponto de entrada de linha de comando main()."""
        with patch(
            "editor.release_tools.configurar_certificado_macos.configurar_keychain_e_certificado_macos",
            return_value=True,
        ):
            codigo = main()
            self.assertEqual(codigo, 0)

    def test_main_retorna_zero_mesmo_quando_pulado(self) -> None:
        """Valida que main() retorna zero para não quebrar o pipeline se o certificado não for provido."""
        with patch(
            "editor.release_tools.configurar_certificado_macos.configurar_keychain_e_certificado_macos",
            return_value=False,
        ):
            codigo = main()
            self.assertEqual(codigo, 0)

    def test_converter_pkcs12_falha_de_senha_ou_corrupcao_lanca_runtime_error(self) -> None:
        """Valida que erro de senha ou corrupção no OpenSSL lança RuntimeError detalhado."""
        caminho_p12 = self.pasta_temp / "original.p12"
        caminho_p12.write_bytes(b"p12_original")

        with patch("subprocess.run") as mock_run:
            erro_proc = subprocess.CalledProcessError(
                1, ["openssl", "pkcs12"], stderr=b"mac verify failure: invalid password"
            )
            mock_run.side_effect = erro_proc

            with self.assertRaises(RuntimeError) as ctx:
                converter_pkcs12_para_formato_compativel_macos(caminho_p12, "senha-errada")
            self.assertIn("senha incorreta ou arquivo corrompido", str(ctx.exception))
            self.assertIn("mac verify failure", str(ctx.exception))

    def test_converter_pkcs12_limpa_pem_temp_mesmo_com_falha_unlink(self) -> None:
        """Garante que a remoção do arquivo PEM temporário trata falhas no unlink sem quebrar."""
        caminho_p12 = self.pasta_temp / "original.p12"
        caminho_p12.write_bytes(b"p12_original")

        caminho_pem = self.pasta_temp / "original_temp_unencrypted.pem"
        caminho_pem.write_bytes(b"pem_secret_data")

        with (
            patch("subprocess.run", return_value=MagicMock(returncode=0)),
            patch.object(Path, "unlink", side_effect=OSError("Permissao negada")),
        ):
            destino = self.pasta_temp / "compat.p12"
            res = converter_pkcs12_para_formato_compativel_macos(caminho_p12, "senha", destino)
            self.assertEqual(res, destino)

    def test_main_captura_excecao_e_retorna_um(self) -> None:
        """Valida que main() captura exceções e retorna código 1."""
        with patch(
            "editor.release_tools.configurar_certificado_macos.configurar_keychain_e_certificado_macos",
            side_effect=RuntimeError("Falha crítica simulada"),
        ):
            codigo = main()
            self.assertEqual(codigo, 1)

    def test_execucao_como_modulo_main(self) -> None:
        """Garante que a execução do módulo via python -m invoca main() e finaliza com sys.exit(0)."""
        import runpy

        with (
            patch.dict(os.environ, {"APPLE_CERT_P12": ""}),
            patch("sys.exit") as mock_exit,
        ):
            runpy.run_module(
                "editor.release_tools.configurar_certificado_macos", run_name="__main__"
            )
            mock_exit.assert_called_once_with(0)
