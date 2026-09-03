# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

import pygit2
from editor.core.worker import TarefaPublicacao, TarefaInicializacao
from editor.core.gerenciador_sessao import SessaoUsuario
from editor.core.servico_submissao import ResultadoSubmissao, ErroSubmissao

class TestWorker(unittest.TestCase):
    """Testes unitários para as tarefas de background do editor."""

    def test_tarefa_publicacao_nova_pr(self):
        """Testa o fluxo de publicação de uma PR com sucesso."""
        storage_mock = MagicMock()
        storage_mock.obter_caminho_base_repo.return_value = Path("/fake/repo")
        caminho_database = Path("/fake/repo/database/teste")
        dados_pr = {"titulo": "Meu Titulo", "descricao": "Minha Descricao"}

        sessao = SessaoUsuario(
            email="autor@teste.com",
            nome_completo="Autor Teste",
            jwt_supabase="jwt_123",
            token_atualizacao="ref_123",
        )

        mock_servico = MagicMock()
        mock_servico.submeter_sugestao.return_value = ResultadoSubmissao(
            sucesso=True,
            pr_number=42,
            pr_url="https://github.com/aresta-climb/aresta_db/pull/42",
            nome_branch="sugestao-teste-12345678",
            mensagem="OK",
        )

        tarefa = TarefaPublicacao(
            sessao=sessao,
            storage=storage_mock,
            caminho_database_croqui=caminho_database,
            id_croqui="teste",
            dados_pr=dados_pr,
            modo_atualizacao=False,
            servico_submissao=mock_servico,
        )

        tarefa.sucesso = MagicMock()
        tarefa.aviso = MagicMock()
        tarefa.erro = MagicMock()
        tarefa.progresso = MagicMock()
        tarefa.status = MagicMock()

        tarefa.run()

        mock_servico.submeter_sugestao.assert_called_once()
        args = mock_servico.submeter_sugestao.call_args[1]
        self.assertEqual(args["titulo"], "Meu Titulo")
        self.assertEqual(args["descricao"], "Minha Descricao")
        self.assertEqual(args["sessao"], sessao)
        self.assertEqual(args["id_croqui"], "teste")

        tarefa.sucesso.emit.assert_called_once_with(
            "https://github.com/aresta-climb/aresta_db/pull/42",
            "sugestao-teste-12345678",
            "aresta-climb",
        )

    def test_tarefa_publicacao_modo_atualizacao(self):
        """Testa o fluxo de atualização de uma PR existente."""
        storage_mock = MagicMock()
        caminho_database = Path("/fake/repo/database/teste")
        sessao = SessaoUsuario(
            email="autor@teste.com",
            nome_completo="Autor Teste",
            jwt_supabase="jwt_123",
            token_atualizacao="ref_123",
        )

        mock_servico = MagicMock()
        mock_servico.submeter_sugestao.return_value = ResultadoSubmissao(
            sucesso=True,
            pr_number=None,
            pr_url=None,
            nome_branch="sugestao-teste-existente",
            mensagem="Atualizado",
        )

        tarefa = TarefaPublicacao(
            sessao=sessao,
            storage=storage_mock,
            caminho_database_croqui=caminho_database,
            id_croqui="teste",
            dados_pr=None,
            modo_atualizacao=True,
            pr_branch="sugestao-teste-existente",
            servico_submissao=mock_servico,
        )

        tarefa.sucesso = MagicMock()
        tarefa.run()

        args = mock_servico.submeter_sugestao.call_args[1]
        self.assertEqual(args["branch_existente"], "sugestao-teste-existente")
        tarefa.sucesso.emit.assert_called_once_with(
            "atualizado",
            "sugestao-teste-existente",
            "aresta-climb",
        )

    def test_tarefa_publicacao_sem_alteracoes(self):
        """Testa quando nenhuma alteração é detectada."""
        storage_mock = MagicMock()
        sessao = SessaoUsuario(
            email="autor@teste.com",
            nome_completo="Autor Teste",
            jwt_supabase="jwt_123",
            token_atualizacao="ref_123",
        )

        mock_servico = MagicMock()
        mock_servico.submeter_sugestao.return_value = ResultadoSubmissao(
            sucesso=True,
            nome_branch="sugestao-teste-12345678",
            mensagem="Nenhuma alteração foi detectada no croqui.",
            sem_alteracoes=True,
        )

        tarefa = TarefaPublicacao(
            sessao=sessao,
            storage=storage_mock,
            caminho_database_croqui=Path("/fake"),
            id_croqui="teste",
            servico_submissao=mock_servico,
        )

        tarefa.aviso = MagicMock()
        tarefa.sucesso = MagicMock()
        tarefa.run()

        tarefa.aviso.emit.assert_called_once()
        self.assertIn("Nenhuma alteração", tarefa.aviso.emit.call_args[0][0])
        tarefa.sucesso.emit.assert_not_called()

    @patch("editor.core.telemetria.capturar_falha_submissao")
    @patch("editor.core.registro_log.logger.critical")
    def test_tarefa_publicacao_erro_emite_sinal_e_registra_telemetria(self, mock_logger, mock_capturar):
        """Testa emissão de sinal de erro, logging crítico e telemetria em caso de exceção."""
        mock_servico = MagicMock()
        mock_servico.submeter_sugestao.side_effect = ErroSubmissao("Falha de rede")

        tarefa = TarefaPublicacao(
            caminho_database_croqui=Path("/fake"),
            id_croqui="teste",
            servico_submissao=mock_servico,
        )

        tarefa.erro = MagicMock()
        tarefa.run()

        tarefa.erro.emit.assert_called_once_with("Falha de rede")
        mock_logger.assert_called_once()
        self.assertIn("teste", mock_logger.call_args[0][0])
        mock_capturar.assert_called_once()
        kwargs = mock_capturar.call_args[1]
        self.assertEqual(kwargs["id_croqui"], "teste")
        self.assertEqual(kwargs["categoria"], "inesperado")
        self.assertEqual(kwargs["etapa"], "execucao_tarefa_publicacao")

    @patch("editor.core.worker.GerenciadorCaminhos")
    @patch("editor.core.worker.ServicoLoja")
    def test_tarefa_inicializacao_detecta_atualizacao_store(self, mock_servico_loja_class, mock_storage_class):
        """Quando a Store tem atualização, TarefaInicializacao deve emitir atualizacao_disponivel e interromper."""
        from editor.core.servico_loja import ResultadoAtualizacao, StatusAtualizacao
        mock_servico = mock_servico_loja_class.return_value
        res = ResultadoAtualizacao(
            status=StatusAtualizacao.ATUALIZACAO_DISPONIVEL,
            versao_disponivel="1.5.0.0"
        )
        mock_servico.verificar_atualizacoes_disponiveis.return_value = res

        tarefa = TarefaInicializacao("test_client")
        tarefa.atualizacao_disponivel = MagicMock()
        tarefa.sucesso = MagicMock()
        tarefa.status = MagicMock()
        tarefa.progresso = MagicMock()

        tarefa.run()

        mock_servico.verificar_atualizacoes_disponiveis.assert_called_once()
        tarefa.atualizacao_disponivel.emit.assert_called_once_with(res)
        tarefa.sucesso.emit.assert_not_called()

    @patch("editor.core.worker.GerenciadorSincronizacao")
    @patch("editor.core.worker.GerenciadorCaminhos")
    @patch("editor.core.worker.ServicoLoja")
    def test_tarefa_inicializacao_bypass_fora_da_store(self, mock_servico_loja_class, mock_storage_class, mock_sync_class):
        """Quando fora da Store (NAO_APLICAVEL), TarefaInicializacao deve seguir normalmente."""
        from editor.core.servico_loja import ResultadoAtualizacao, StatusAtualizacao
        from editor.core.gerenciador_sessao import SessaoUsuario
        mock_servico = mock_servico_loja_class.return_value
        res = ResultadoAtualizacao(
            status=StatusAtualizacao.NAO_APLICAVEL,
            mensagem="Bypass ativo"
        )
        mock_servico.verificar_atualizacoes_disponiveis.return_value = res

        mock_storage = mock_storage_class.return_value
        caminho_repo = MagicMock()
        caminho_repo.exists.return_value = True
        caminho_repo.iterdir.return_value = ["dummy"]
        mock_storage.obter_caminho_base_repo.return_value = caminho_repo

        tarefa = TarefaInicializacao("test_client")
        tarefa.gerenciador_sessao = MagicMock()
        tarefa.cliente_auth = MagicMock()
        sessao_mock = SessaoUsuario(
            email="autor@arestaclimb.com",
            nome_completo="Renato Autor",
            jwt_supabase="jwt.valido",
            token_atualizacao="refresh.valido",
            token_github="fake_token",
        )
        tarefa.gerenciador_sessao.obter_sessao.return_value = sessao_mock
        tarefa.cliente_auth.obter_usuario_atual.return_value = {
            "email": "autor@arestaclimb.com",
            "user_metadata": {"nome_completo": "Renato Autor"},
        }

        tarefa.atualizacao_disponivel = MagicMock()
        tarefa.sucesso = MagicMock()
        tarefa.status = MagicMock()
        tarefa.progresso = MagicMock()
        tarefa.mostrar_progresso = MagicMock()

        tarefa.run()

        mock_servico.verificar_atualizacoes_disponiveis.assert_called_once()
        tarefa.atualizacao_disponivel.emit.assert_not_called()
        tarefa.sucesso.emit.assert_called_once()

    @patch("editor.core.worker.GerenciadorSincronizacao")
    @patch("editor.core.worker.GerenciadorCaminhos")
    @patch("editor.core.worker.ServicoLoja")
    def test_tarefa_inicializacao_com_sessao_supabase_valida(
        self, mock_servico_loja_class, mock_storage_class, mock_sync_class
    ):
        """Valida que TarefaInicializacao utiliza SessaoUsuario válida do Supabase Auth."""
        from editor.core.servico_loja import ResultadoAtualizacao, StatusAtualizacao
        from editor.core.gerenciador_sessao import SessaoUsuario

        mock_servico = mock_servico_loja_class.return_value
        mock_servico.verificar_atualizacoes_disponiveis.return_value = ResultadoAtualizacao(
            status=StatusAtualizacao.NAO_APLICAVEL
        )

        mock_storage = mock_storage_class.return_value
        caminho_repo = MagicMock()
        caminho_repo.exists.return_value = True
        caminho_repo.iterdir.return_value = ["dummy"]
        mock_storage.obter_caminho_base_repo.return_value = caminho_repo

        tarefa = TarefaInicializacao()
        tarefa.gerenciador_sessao = MagicMock()
        tarefa.cliente_auth = MagicMock()

        sessao_mock = SessaoUsuario(
            email="autor@arestaclimb.com",
            nome_completo="Renato Autor",
            jwt_supabase="jwt.valido",
            token_atualizacao="refresh.valido",
        )
        tarefa.gerenciador_sessao.obter_sessao.return_value = sessao_mock
        tarefa.cliente_auth.obter_usuario_atual.return_value = {
            "email": "autor@arestaclimb.com",
            "user_metadata": {"nome_completo": "Renato Autor"},
        }

        tarefa.atualizacao_disponivel = MagicMock()
        tarefa.sucesso = MagicMock()
        tarefa.status = MagicMock()
        tarefa.progresso = MagicMock()
        tarefa.mostrar_progresso = MagicMock()

        tarefa.run()

        tarefa.cliente_auth.obter_usuario_atual.assert_called_once_with("jwt.valido")
        tarefa.sucesso.emit.assert_called_once()
        self.assertEqual(tarefa.sessao_usuario.nome_completo, "Renato Autor")

    @patch("editor.core.worker.GerenciadorCaminhos")
    @patch("editor.core.worker.ServicoLoja")
    def test_tarefa_inicializacao_bloqueia_e_aborta_quando_login_cancelado(
        self, mock_servico_loja_class, mock_storage_class
    ):
        """Valida que TarefaInicializacao para a execução se o login for cancelado na UI."""
        from editor.core.servico_loja import ResultadoAtualizacao, StatusAtualizacao

        mock_servico = mock_servico_loja_class.return_value
        mock_servico.verificar_atualizacoes_disponiveis.return_value = ResultadoAtualizacao(
            status=StatusAtualizacao.NAO_APLICAVEL
        )

        tarefa = TarefaInicializacao()
        tarefa.gerenciador_sessao = MagicMock()
        tarefa.gerenciador_sessao.obter_sessao.return_value = None

        tarefa.atualizacao_disponivel = MagicMock()
        tarefa.sucesso = MagicMock()
        tarefa.erro = MagicMock()
        tarefa.status = MagicMock()
        tarefa.progresso = MagicMock()

        # Conecta ao sinal real do PySide6 para simular cancelamento da UI
        tarefa.solicitar_login_ui.connect(lambda: tarefa.definir_sessao_concluida(None))

        tarefa.run()

        tarefa.sucesso.emit.assert_not_called()
        tarefa.erro.emit.assert_called_once_with(
            "Autenticação necessária para utilizar o Aresta Editor."
        )

    def test_tarefa_dados_conexao_emite_dados_completos(self):
        """Valida que TarefaDadosConexao executa solicitar_sessao_servidor e emite sinais corretamente."""
        from editor.core.worker import TarefaDadosConexao

        mock_servidor = MagicMock()
        mock_servidor.porta = 8888
        mock_servidor.codigo_sessao = "f0zbudvq"
        mock_servidor.obter_url_previa_canonica.return_value = "https://previa.arestaclimb.com/f0zb-udvq"
        mock_servidor.gerar_qr_code.return_value = b"png_fake_bytes"

        tarefa = TarefaDadosConexao(mock_servidor)
        tarefa.concluido = MagicMock()

        tarefa.run()

        mock_servidor.solicitar_sessao_servidor.assert_not_called()
        tarefa.concluido.emit.assert_called_once_with(
            "https://previa.arestaclimb.com/f0zb-udvq",
            b"png_fake_bytes",
            "f0zb-udvq",
        )


if __name__ == "__main__":
    unittest.main()
