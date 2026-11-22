# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import tempfile
import unittest

from tests.validador_tipagem import (
    executar_verificacao_mypy,
    verificar_anotacoes_ast,
    verificar_arquivo_ast,
)


class TestValidadorTipagem(unittest.TestCase):
    def test_executar_verificacao_mypy_codigo_valido(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("def soma(a: int, b: int) -> int:\n    return a + b\n")
            temp_name = f.name

        try:
            codigo, stdout, stderr = executar_verificacao_mypy([temp_name])
            self.assertEqual(codigo, 0, f"Mypy falhou inesperadamente: {stdout} {stderr}")
        finally:
            os.remove(temp_name)

    def test_executar_verificacao_mypy_codigo_invalido(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("def texto() -> str:\n    return 123\n")
            temp_name = f.name

        try:
            codigo, stdout, stderr = executar_verificacao_mypy([temp_name])
            self.assertNotEqual(codigo, 0)
            self.assertIn("error", stdout.lower())
        finally:
            os.remove(temp_name)

    def test_executar_verificacao_mypy_ignora_subcaminhos_aresta_api_no_sys_path(self) -> None:
        import sys
        from pathlib import Path

        raiz = Path(__file__).resolve().parent.parent
        config_path = str(raiz / "pyproject.toml")
        alvo = str((raiz / "aresta_api" / "src" / "gerador_openapi.py").resolve())
        caminho_poluido = str((raiz / "aresta_api" / "src").resolve())

        sys.path.insert(0, caminho_poluido)
        try:
            codigo, stdout, stderr = executar_verificacao_mypy([alvo], config_path=config_path)
            self.assertEqual(codigo, 0, f"{stdout}\n{stderr}")
        finally:
            if caminho_poluido in sys.path:
                sys.path.remove(caminho_poluido)

    def test_verificar_anotacoes_ast_funcao_completa(self) -> None:
        codigo = """
def processar(nome: str, valor: int = 0) -> bool:
    return True

class Exemplo:
    def metodo(self, x: float) -> str:
        return str(x)

    @classmethod
    def criar(cls, dado: str) -> "Exemplo":
        return cls()
"""
        erros = verificar_anotacoes_ast(codigo)
        self.assertEqual(erros, [])

    def test_verificar_anotacoes_ast_parametro_sem_anotacao(self) -> None:
        codigo = """
def calcular(x, y: int) -> int:
    return x + y
"""
        erros = verificar_anotacoes_ast(codigo)
        self.assertEqual(len(erros), 1)
        self.assertIn("calcular", erros[0])
        self.assertIn("x", erros[0])

    def test_verificar_anotacoes_ast_vararg_e_kwarg(self) -> None:
        codigo_invalido = """
def funcao_varargs(*args, **kwargs) -> None:
    pass
"""
        erros = verificar_anotacoes_ast(codigo_invalido)
        self.assertEqual(len(erros), 2)
        self.assertIn("*args", erros[0])
        self.assertIn("**kwargs", erros[1])

        codigo_valido = """
def funcao_varargs_valida(*args: int, **kwargs: str) -> None:
    pass
"""
        erros_validos = verificar_anotacoes_ast(codigo_valido)
        self.assertEqual(erros_validos, [])

    def test_verificar_anotacoes_ast_retorno_sem_anotacao(self) -> None:
        codigo = """
def somar(a: int, b: int):
    return a + b
"""
        erros = verificar_anotacoes_ast(codigo)
        self.assertEqual(len(erros), 1)
        self.assertIn("somar", erros[0])
        self.assertIn("não possui anotação de tipo de retorno", erros[0])

    def test_verificar_arquivo_ast(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("def teste(arg: str) -> None:\n    pass\n")
            temp_name = f.name

        try:
            erros = verificar_arquivo_ast(temp_name)
            self.assertEqual(erros, [])
        finally:
            os.remove(temp_name)


if __name__ == "__main__":
    unittest.main()
