# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import unittest
from pathlib import Path
from tests.validador_tipagem import (
    executar_verificacao_mypy,
    verificar_arquivo_ast,
)


class TestTipagemEstaticaArestaDb(unittest.TestCase):
    def setUp(self) -> None:
        self.raiz_projeto = Path(__file__).resolve().parent.parent
        self.pyproject_path = str(self.raiz_projeto / "pyproject.toml")

    def test_conformidade_mypy_infraestrutura_onda_1(self) -> None:
        """Valida que os módulos de infraestrutura da Onda 1 passam no MyPy estrito."""
        arquivos_verificar = [
            str(self.raiz_projeto / "tests" / "validador_tipagem.py"),
            str(self.raiz_projeto / "aresta_api" / "build.py"),
        ]

        codigo, stdout, stderr = executar_verificacao_mypy(
            arquivos_verificar,
            config_path=self.pyproject_path,
        )
        self.assertEqual(
            codigo,
            0,
            f"Erros detectados pelo MyPy estrito na raiz do aresta_db:\n{stdout}\n{stderr}",
        )

    def test_anotacoes_ast_validador_tipagem(self) -> None:
        """Garante que todas as funções e métodos de validador_tipagem.py possuem anotações completas."""
        caminho_validador = str(self.raiz_projeto / "tests" / "validador_tipagem.py")
        erros = verificar_arquivo_ast(caminho_validador)
        self.assertEqual(
            erros,
            [],
            f"Funções sem anotação em validador_tipagem.py: {erros}",
        )

    def test_stubs_protobuf_gerados_existem(self) -> None:
        """Garante que os stubs .pyi foram gerados para todos os esquemas Protobuf da aresta_api."""
        generated_dir = self.raiz_projeto / "aresta_api" / "proto" / "generated"

        protos_esperados = [
            "beta_pb2.pyi",
            "croqui_pb2.pyi",
            "croqui_experimental_pb2.pyi",
            "indice_pb2.pyi",
            "serving_pb2.pyi",
        ]

        for stub in protos_esperados:
            caminho_stub = generated_dir / stub
            self.assertTrue(
                caminho_stub.exists(),
                f"Arquivo de stub {stub} não foi encontrado em {generated_dir}",
            )


if __name__ == "__main__":
    unittest.main()
