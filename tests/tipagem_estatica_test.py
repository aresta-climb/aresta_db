# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import unittest
from pathlib import Path
from tests.validador_tipagem import (
    executar_verificacao_mypy,
    verificar_arquivo_ast,
)

DIRETORIOS_IGNORADOS = {
    ".git",
    "generated",
    "database",
    ".pytest_cache",
    "__pycache__",
    "venv",
    ".venv",
    ".agent",
    ".agents",
    ".gemini",
    "scratch",
}


def obter_todos_arquivos_producao_py(raiz: Path) -> list[str]:
    """
    Descobre dinamicamente todos os arquivos .py de código de produção
    no repositório aresta_db e no submódulo aresta_api (ignorando diretórios gerados,
    temporários, caches e arquivos de teste).
    """
    arquivos: list[str] = []
    for p in raiz.rglob("*.py"):
        if any(part in DIRETORIOS_IGNORADOS for part in p.parts):
            continue
        if p.name.endswith("_test.py") or p.name.startswith("test_") or "tests" in p.parts:
            continue
        arquivos.append(str(p.resolve()))
    return sorted(arquivos)


class TestTipagemEstaticaArestaDb(unittest.TestCase):
    def setUp(self) -> None:
        self.raiz_projeto = Path(__file__).resolve().parent.parent
        self.pyproject_path = str(self.raiz_projeto / "pyproject.toml")
        self.arquivos_producao = obter_todos_arquivos_producao_py(self.raiz_projeto)

    def test_descoberta_arquivos_producao_nao_vazia(self) -> None:
        """Garante que a descoberta dinâmica encontra todos os módulos de produção."""
        self.assertGreaterEqual(
            len(self.arquivos_producao),
            120,
            f"Quantidade de arquivos de produção menor que o esperado: {len(self.arquivos_producao)}",
        )

    def test_conformidade_mypy_todos_arquivos_producao(self) -> None:
        """
        Valida que 100% dos arquivos Python de produção do repositório
        passam com zero erros na verificação estrita do MyPy (--strict).
        """
        codigo, stdout, stderr = executar_verificacao_mypy(
            self.arquivos_producao,
            config_path=self.pyproject_path,
        )
        self.assertEqual(
            codigo,
            0,
            f"Erros detectados pelo MyPy estrito em arquivos de produção:\n{stdout}\n{stderr}",
        )

    def test_anotacoes_ast_todos_arquivos_producao(self) -> None:
        """
        Garante que 100% das funções, métodos e retornos em todos os arquivos
        de produção do repositório possuem anotações de tipo completas.
        """
        erros_totais: list[str] = []
        for caminho_arquivo in self.arquivos_producao:
            erros_arquivo = verificar_arquivo_ast(caminho_arquivo)
            erros_totais.extend(erros_arquivo)

        self.assertEqual(
            erros_totais,
            [],
            f"Funções/métodos sem anotação completa encontrados na base de produção:\n"
            + "\n".join(erros_totais),
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





