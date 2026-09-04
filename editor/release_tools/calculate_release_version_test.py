# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from unittest.mock import patch
import io
import tempfile
from pathlib import Path

from editor.release_tools.calculate_release_version import (
    calcular_versao_release,
    extrair_versao_de_arquivo,
    main,
)

class TestCalculateReleaseVersion(unittest.TestCase):
    """Testes unitários para cálculo da versão oficial de release (TDD - 100% Cobertura)."""

    def test_calcular_patch_de_versao_dev(self):
        """Versão -dev com patch deve simplesmente remover o sufixo -dev."""
        resultado = calcular_versao_release("0.2.1-dev", "patch")
        self.assertEqual(resultado, "0.2.1")

    def test_calcular_patch_de_versao_limpa(self):
        """Versão limpa sem -dev deve incrementar o patch em 1."""
        resultado = calcular_versao_release("0.2.0", "patch")
        self.assertEqual(resultado, "0.2.1")

    def test_calcular_minor_de_versao_dev(self):
        """Versão -dev com minor deve incrementar o minor e zerar o patch."""
        resultado = calcular_versao_release("0.2.1-dev", "minor")
        self.assertEqual(resultado, "0.3.0")

    def test_calcular_minor_de_versao_limpa(self):
        """Versão limpa com minor deve incrementar o minor e zerar o patch."""
        resultado = calcular_versao_release("0.2.0", "minor")
        self.assertEqual(resultado, "0.3.0")

    def test_calcular_major_de_versao_dev(self):
        """Versão -dev com major deve incrementar o major e zerar minor e patch."""
        resultado = calcular_versao_release("0.2.1-dev", "major")
        self.assertEqual(resultado, "1.0.0")

    def test_calcular_major_de_versao_limpa(self):
        """Versão limpa com major deve incrementar o major e zerar minor e patch."""
        resultado = calcular_versao_release("0.2.0", "major")
        self.assertEqual(resultado, "1.0.0")

    def test_calcular_custom_valida(self):
        """Quando tipo for custom e a versão for estritamente maior, deve retornar a versão customizada."""
        resultado = calcular_versao_release("0.2.1-dev", "custom", custom="0.5.0")
        self.assertEqual(resultado, "0.5.0")

    def test_calcular_custom_sem_versao_informada(self):
        """Quando tipo for custom mas nenhuma versão for fornecida, deve levantar ValueError."""
        with self.assertRaises(ValueError) as ctx:
            calcular_versao_release("0.2.1-dev", "custom", custom=None)
        self.assertIn("Versão customizada obrigatória", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            calcular_versao_release("0.2.1-dev", "custom", custom="   ")
        self.assertIn("Versão customizada obrigatória", str(ctx.exception))

    def test_calcular_custom_invalida_semver(self):
        """Versão customizada que não siga SemVer deve levantar ValueError."""
        with self.assertRaises(ValueError) as ctx:
            calcular_versao_release("0.2.1-dev", "custom", custom="invalido")
        self.assertIn("não segue o formato SemVer", str(ctx.exception))

    def test_calcular_custom_menor_ou_igual(self):
        """Versão customizada que não seja estritamente superior à atual deve levantar ValueError."""
        with self.assertRaises(ValueError) as ctx:
            calcular_versao_release("0.2.1-dev", "custom", custom="0.2.0")
        self.assertIn("deve ser estritamente maior", str(ctx.exception))

    def test_tipo_bump_invalido(self):
        """Tipo de incremento desconhecido deve levantar ValueError."""
        with self.assertRaises(ValueError) as ctx:
            calcular_versao_release("0.2.1-dev", "super_bump")
        self.assertIn("Tipo de incremento inválido", str(ctx.exception))

    def test_versao_atual_invalida(self):
        """Versão atual que não siga o formato SemVer deve levantar ValueError."""
        with self.assertRaises(ValueError) as ctx:
            calcular_versao_release("versao_errada", "patch")
        self.assertIn("Versão atual inválida", str(ctx.exception))

    def test_extrair_versao_de_arquivo_sucesso(self):
        """Deve extrair corretamente a versão a partir de um arquivo python."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho = Path(tmp_dir) / "version.py"
            caminho.write_text('VERSION: str = "1.2.3-dev"\n', encoding="utf-8")
            versao = extrair_versao_de_arquivo(caminho)
            self.assertEqual(versao, "1.2.3-dev")

    def test_extrair_versao_de_arquivo_nao_encontrado(self):
        """Deve levantar FileNotFoundError se o arquivo não existir."""
        with self.assertRaises(FileNotFoundError):
            extrair_versao_de_arquivo("caminho_inexistente_12345.py")

    def test_extrair_versao_de_arquivo_padrao_nao_encontrado(self):
        """Deve levantar ValueError se o arquivo existir mas não contiver o padrão VERSION."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho = Path(tmp_dir) / "version.py"
            caminho.write_text('FOO = "bar"\n', encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                extrair_versao_de_arquivo(caminho)
            self.assertIn("Padrão VERSION não encontrado", str(ctx.exception))

    def test_cli_com_versao_atual_imprime_versao(self):
        """CLI deve calcular e imprimir a versão na saída padrão com código de saída 0."""
        saida = io.StringIO()
        with patch("sys.stdout", saida):
            codigo = main(["--versao-atual", "0.2.1-dev", "--tipo", "patch"])
            self.assertEqual(codigo, 0)
            self.assertEqual(saida.getvalue().strip(), "0.2.1")

    def test_cli_com_arquivo_imprime_versao(self):
        """CLI deve ler do arquivo informado e calcular a versão."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho = Path(tmp_dir) / "version.py"
            caminho.write_text('VERSION: str = "0.2.1-dev"\n', encoding="utf-8")
            saida = io.StringIO()
            with patch("sys.stdout", saida):
                codigo = main(["--arquivo", str(caminho), "--tipo", "minor"])
                self.assertEqual(codigo, 0)
                self.assertEqual(saida.getvalue().strip(), "0.3.0")

    def test_cli_com_erro_retorna_codigo_1_e_escreve_stderr(self):
        """CLI deve capturar erros, imprimir em stderr e retornar código de saída 1."""
        saida_erro = io.StringIO()
        with patch("sys.stderr", saida_erro):
            codigo = main(["--versao-atual", "0.2.1-dev", "--tipo", "custom", "--custom", ""])
            self.assertEqual(codigo, 1)
            self.assertIn("Erro:", saida_erro.getvalue())

if __name__ == "__main__":
    unittest.main()
