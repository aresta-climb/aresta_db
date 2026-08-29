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

    ARQUIVOS_CORE_ONDA_2 = [
        "editor/core/version.py",
        "editor/core/formatacao.py",
        "editor/core/storage.py",
        "editor/core/contexto.py",
        "editor/core/coordenadas.py",
        "editor/core/geometrias_poi.py",
        "editor/core/croqui_format.py",
        "editor/core/croqui_experimental.py",
        "editor/core/proto_comments.py",
        "editor/core/workspace.py",
        "editor/core/processamento_imagem_campo.py",
        "editor/core/imagens_markdown.py",
        "editor/core/imagem_anonimizada.py",
        "editor/core/gerenciador_sessao.py",
        "editor/core/cliente_auth_supabase.py",
        "editor/core/servico_submissao.py",
        "editor/core/servico_loja.py",
        "editor/core/sync.py",
        "editor/core/worker.py",
        "editor/core/atualizador_ui.py",
        "editor/core/monitor_inatividade.py",
        "editor/core/servidor_celular.py",
        "editor/core/servidor_oauth_callback.py",
        "editor/core/historico.py",
        "editor/core/diario.py",
        "editor/core/registro_log.py",
        "editor/core/telemetria.py",
    ]

    def test_conformidade_mypy_editor_core_onda_2(self) -> None:
        """Valida que todos os módulos do núcleo de dados (editor/core) passam no MyPy estrito."""
        arquivos_verificar = [
            str(self.raiz_projeto / caminho)
            for caminho in self.ARQUIVOS_CORE_ONDA_2
        ]

        codigo, stdout, stderr = executar_verificacao_mypy(
            arquivos_verificar,
            config_path=self.pyproject_path,
        )
        self.assertEqual(
            codigo,
            0,
            f"Erros detectados pelo MyPy estrito nos módulos de editor/core:\n{stdout}\n{stderr}",
        )

    def test_anotacoes_ast_editor_core_onda_2(self) -> None:
        """Garante que todas as funções, métodos e retornos em editor/core possuem anotações de tipo completas."""
        erros_totais: list[str] = []
        for caminho_relativo in self.ARQUIVOS_CORE_ONDA_2:
            caminho_completo = str(self.raiz_projeto / caminho_relativo)
            erros_arquivo = verificar_arquivo_ast(caminho_completo)
            erros_totais.extend(erros_arquivo)

        self.assertEqual(
            erros_totais,
            [],
            f"Funções/métodos sem anotação completa encontrados em editor/core:\n"
            + "\n".join(erros_totais),
        )

    ARQUIVOS_ONDA_3 = [
        "editor/commands/comandos_protobuf.py",
        "editor/commands/comandos_mapas.py",
        "editor/controllers/croqui_controller.py",
        "editor/controllers/compilacao_controller.py",
        "editor/controllers/mapas_controller.py",
        "editor/controllers/publish_controller.py",
        "editor/build.py",
    ]

    def test_conformidade_mypy_onda_3(self) -> None:
        """Valida que todos os módulos de comandos e controladores da Onda 3 passam no MyPy estrito."""
        arquivos_verificar = [
            str(self.raiz_projeto / caminho)
            for caminho in self.ARQUIVOS_ONDA_3
        ]

        codigo, stdout, stderr = executar_verificacao_mypy(
            arquivos_verificar,
            config_path=self.pyproject_path,
        )
        self.assertEqual(
            codigo,
            0,
            f"Erros detectados pelo MyPy estrito nos módulos da Onda 3:\n{stdout}\n{stderr}",
        )

    def test_anotacoes_ast_onda_3(self) -> None:
        """Garante que todas as funções, métodos e retornos nos módulos da Onda 3 possuem anotações de tipo completas."""
        erros_totais: list[str] = []
        for caminho_relativo in self.ARQUIVOS_ONDA_3:
            caminho_completo = str(self.raiz_projeto / caminho_relativo)
            erros_arquivo = verificar_arquivo_ast(caminho_completo)
            erros_totais.extend(erros_arquivo)

        self.assertEqual(
            erros_totais,
            [],
            f"Funções/métodos sem anotação completa encontrados na Onda 3:\n"
            + "\n".join(erros_totais),
        )

    ARQUIVOS_ONDA_4 = [
        "editor/models/croqui_model.py",
        "editor/models/compilacao_log.py",
        "editor/views/estilo.py",
        "editor/views/notificacao.py",
        "editor/views/publish_dialog.py",
        "editor/views/tela_de_abertura.py",
        "editor/views/dialogo_recuperacao_sessao.py",
        "editor/views/tree_view_adapter.py",
        "editor/views/protobuf_widget_factory.py",
        "editor/views/widget_campo_coordenada_e7.py",
        "editor/views/widget_campo_imagem.py",
        "editor/views/widget_editor_dados.py",
        "editor/views/widget_editor_mapas.py",
        "editor/views/widget_mensagem_coordenada.py",
        "editor/views/widget_painel_referencias.py",
        "editor/views/widget_saida_compilacao.py",
        "editor/views/dialogos/dialogo_criar_pico.py",
        "editor/views/dialogos/dialogo_criar_setor_ou_grupo.py",
        "editor/views/dialogos/dialogo_criar_escalada.py",
        "editor/views/dialogos/dialogo_criar_botao.py",
        "editor/views/dialogos/dialogo_adicionar_mapa.py",
        "editor/views/dialogos/dialogo_busca_referencia.py",
        "editor/views/dialogos/dialogo_inserir_imagem_markdown.py",
        "editor/views/dialogos/dialogo_perfil_autor.py",
        "editor/legacy_views/dialogo_busca_croqui.py",
        "editor/legacy_views/dialogo_conexao_celular.py",
        "editor/legacy_views/tela_de_carregamento.py",
        "editor/legacy_views/widget_editor_imagens.py",
        "editor/legacy_views/area_principal.py",
        "editor/main.py",
    ]

    def test_conformidade_mypy_onda_4(self) -> None:
        """Valida que todos os módulos de Views, Modelos e Diálogos da Onda 4 passam no MyPy estrito."""
        arquivos_verificar = [
            str(self.raiz_projeto / caminho)
            for caminho in self.ARQUIVOS_ONDA_4
        ]

        codigo, stdout, stderr = executar_verificacao_mypy(
            arquivos_verificar,
            config_path=self.pyproject_path,
        )
        self.assertEqual(
            codigo,
            0,
            f"Erros detectados pelo MyPy estrito nos módulos da Onda 4:\n{stdout}\n{stderr}",
        )

    def test_anotacoes_ast_onda_4(self) -> None:
        """Garante que todas as funções, métodos e retornos nos módulos da Onda 4 possuem anotações de tipo completas."""
        erros_totais: list[str] = []
        for caminho_relativo in self.ARQUIVOS_ONDA_4:
            caminho_completo = str(self.raiz_projeto / caminho_relativo)
            erros_arquivo = verificar_arquivo_ast(caminho_completo)
            erros_totais.extend(erros_arquivo)

        self.assertEqual(
            erros_totais,
            [],
            f"Funções/métodos sem anotação completa encontrados na Onda 4:\n"
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



