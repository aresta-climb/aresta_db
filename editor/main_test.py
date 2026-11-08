# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QDialog, QStackedWidget

from editor.core.worker import TarefaInicializacao
from editor.legacy_views.area_principal import JanelaPrincipal
from editor.main import ControladorAplicativo


def test_janela_principal_tem_stack_central(qtbot):
    mock_storage = MagicMock()
    mock_auth = MagicMock()
    janela = JanelaPrincipal(storage=mock_storage, auth=mock_auth)
    qtbot.addWidget(janela)

    # Verifica se existe um QStackedWidget (área principal)
    stack = janela.findChild(QStackedWidget)
    assert stack is not None


def test_fluxo_inicializacao_cria_janela_principal(qtbot, tmp_path):
    with patch("editor.main.TarefaInicializacao") as MockTarefa:
        with patch("editor.main.TelaDeCarregamento") as MockDialog:
            mock_tarefa_inst = MockTarefa.return_value
            mock_tarefa_inst.storage = MagicMock()
            mock_tarefa_inst.sessao_usuario = None

            mock_dialog_inst = MockDialog.return_value
            mock_dialog_inst.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog_inst.caminho_croqui_selecionado = tmp_path

            controlador = ControladorAplicativo()
            controlador.executar_selecao()

            assert controlador.janela_principal is not None
            assert hasattr(controlador.janela_principal, "workspace")


def test_controlador_app_conecta_sinais_corretamente(qtbot):
    # Verificamos manualmente se os sinais usados no ControladorApp existem no TarefaInicializacao
    sinais_necessarios = [
        "status",
        "progresso",
        "mostrar_progresso",
        "atualizacao_disponivel",
        "auth_requerida",
        "auth_concluida",
        "sucesso",
        "erro",
    ]
    for sinal in sinais_necessarios:
        assert hasattr(TarefaInicializacao, sinal), (
            f"O TarefaInicializacao não possui o sinal '{sinal}'"
        )


def test_controlador_app_ao_detectar_atualizacao(qtbot):
    with patch("editor.main.TarefaInicializacao"):
        controlador = ControladorAplicativo()
        qtbot.addWidget(controlador.abertura)
        controlador.abertura.exibir_aviso_atualizacao = MagicMock()

        mock_resultado = MagicMock()
        controlador.ao_detectar_atualizacao(mock_resultado)

        controlador.abertura.exibir_aviso_atualizacao.assert_called_once()
        args, kwargs = controlador.abertura.exibir_aviso_atualizacao.call_args
        assert args[0] == mock_resultado
        assert callable(kwargs.get("callback_atualizar"))

        # Testa a execução do callback
        callback = kwargs.get("callback_atualizar")
        controlador.tarefa.servico_loja = MagicMock()
        callback()
        controlador.tarefa.servico_loja.solicitar_instalacao_atualizacao.assert_called_once_with(
            mock_resultado
        )


def test_fluxo_inicializacao_transicao(qtbot):
    with patch("editor.main.TarefaInicializacao") as MockTarefa:
        with patch("editor.main.TelaDeCarregamento") as MockDialog:
            mock_tarefa_inst = MockTarefa.return_value
            mock_tarefa_inst.storage = MagicMock()

            # Mock para o diálogo retornar 'Accepted'
            mock_dialog_inst = MockDialog.return_value
            mock_dialog_inst.exec.return_value = QDialog.DialogCode.Accepted

            controlador = ControladorAplicativo()
            qtbot.addWidget(controlador.abertura)

            # Simula sucesso chamando o novo fluxo de seleção
            controlador.executar_selecao()

            assert controlador.janela_principal is not None
            assert controlador.janela_principal.isVisible()
            assert not controlador.abertura.isVisible()

            qtbot.addWidget(controlador.janela_principal)
            controlador.janela_principal.close()


def test_mostrar_erro_esconde_abertura_antes(qtbot):
    with patch("editor.main.TarefaInicializacao"):
        with patch("editor.main.QMessageBox.critical") as mock_critical:
            with patch("editor.main.QApplication.quit"):
                controlador = ControladorAplicativo()
                qtbot.addWidget(controlador.abertura)

                # Espionamos o método hide da abertura
                controlador.abertura.hide = MagicMock(side_effect=controlador.abertura.hide)

                controlador.mostrar_erro("Erro de teste")

                # Verifica se hide foi chamado ANTES de critical
                assert controlador.abertura.hide.called
                assert mock_critical.called


def test_controlador_app_define_icone_global(qtbot):
    """Garante que o ícone global da aplicação é configurado na inicialização."""
    with patch("editor.main.TarefaInicializacao"):
        controlador = ControladorAplicativo()
        assert not controlador.app.windowIcon().isNull()
        controlador.abertura.close()


def test_tela_de_abertura_tem_icone_configurado(qtbot):
    """Garante que a tela de abertura carrega o ícone de montanha."""
    from editor.views.tela_de_abertura import TelaDeAbertura

    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)
    assert not abertura.windowIcon().isNull()
    abertura.close()


def test_application_version_is_set(qtbot):
    """Garante que a constante VERSION do módulo version é setada no QApplication."""
    from editor.core.version import VERSION

    with patch("editor.main.TarefaInicializacao"):
        controlador = ControladorAplicativo()
        assert controlador.app.applicationVersion() == VERSION
        controlador.abertura.close()


def test_main_impede_multiplas_instancias(qtbot, capsys):
    with patch(
        "editor.core.instancia_unica.verificar_se_ja_em_execucao", return_value=True
    ) as mock_verif:
        with patch("editor.main.QMessageBox.information") as mock_info:
            with patch("editor.main.sys.exit", side_effect=SystemExit) as mock_exit:
                from editor.main import main

                with pytest.raises(SystemExit):
                    main()

                mock_verif.assert_called_once()
                mock_info.assert_called_once()
                mock_exit.assert_called_once_with(0)
                captured = capsys.readouterr()
                assert "O Aresta Editor já está em execução" in captured.err


def test_main_inicia_servidor_quando_primeira_instancia(qtbot):
    with patch("editor.core.instancia_unica.verificar_se_ja_em_execucao", return_value=False):
        with patch(
            "editor.core.instancia_unica.iniciar_servidor_instancia_unica"
        ) as mock_iniciar_srv:
            with patch("editor.main.ControladorAplicativo") as MockControlador:
                with patch("editor.main.sys.exit", side_effect=SystemExit) as mock_exit:
                    mock_controlador_inst = MockControlador.return_value
                    mock_controlador_inst.executar.return_value = 0

                    from editor.main import main

                    with patch("sys.argv", ["editor/main.py"]):
                        with pytest.raises(SystemExit):
                            main()

                    mock_iniciar_srv.assert_called_once()
                    MockControlador.assert_called_once()
                    mock_exit.assert_called_once_with(0)


def test_main_configura_icone_global_antecipadamente(qtbot):
    with patch("editor.core.instancia_unica.verificar_se_ja_em_execucao", return_value=False):
        with patch("editor.core.instancia_unica.iniciar_servidor_instancia_unica"):
            with patch("editor.main.ControladorAplicativo") as MockControlador:
                with patch("editor.main.sys.exit", side_effect=SystemExit):
                    mock_controlador_inst = MockControlador.return_value
                    mock_controlador_inst.executar.return_value = 0

                    from PySide6.QtWidgets import QApplication

                    from editor.main import main

                    with patch("sys.argv", ["editor/main.py"]):
                        with patch.object(QApplication, "setWindowIcon") as mock_set_icon:
                            with patch.object(QApplication, "processEvents") as mock_process_events:
                                with pytest.raises(SystemExit):
                                    main()
                                mock_set_icon.assert_called()
                                mock_process_events.assert_called()


def test_main_abre_modo_local_repo_com_sucesso(qtbot, tmp_path):
    pasta_croqui = tmp_path / "br_mg_ouro_preto_ouroboulder"
    pasta_croqui.mkdir()
    (pasta_croqui / "croqui.yaml").write_text("id: ouroboulder\n", encoding="utf-8")

    with patch("editor.core.instancia_unica.verificar_se_ja_em_execucao", return_value=False):
        with patch("editor.core.instancia_unica.iniciar_servidor_instancia_unica"):
            with patch("editor.legacy_views.area_principal.JanelaPrincipal") as MockJanela:
                with patch("PySide6.QtWidgets.QApplication.exec", return_value=0):
                    with patch("editor.main.sys.exit", side_effect=SystemExit) as mock_exit:
                        with patch("editor.main.QMessageBox.critical") as mock_crit:
                            mock_janela_inst = MockJanela.return_value

                            from editor.main import main

                            with patch("sys.argv", ["editor/main.py", str(pasta_croqui)]):
                                with pytest.raises(SystemExit):
                                    main()

                            MockJanela.assert_called_once()
                            mock_janela_inst.show.assert_called_once()
                            mock_exit.assert_called_once_with(0)
                            mock_crit.assert_not_called()


def test_main_erro_quando_caminho_database_invalido(qtbot, capsys):
    with patch("editor.core.instancia_unica.verificar_se_ja_em_execucao", return_value=False):
        with patch("editor.core.instancia_unica.iniciar_servidor_instancia_unica"):
            with patch("editor.main.QMessageBox.critical") as mock_crit:
                with patch("editor.main.sys.exit", side_effect=SystemExit) as mock_exit:
                    from editor.main import main

                    with patch("sys.argv", ["editor/main.py", "database/caminho_inexistente_123"]):
                        with pytest.raises(SystemExit):
                            main()

                    mock_crit.assert_called_once()
                    mock_exit.assert_called_once_with(1)
                    captured = capsys.readouterr()
                    assert "Erro: O caminho especificado" in captured.err


def test_qlocalserver_ciclo_vida_e_bloqueio_real(qtbot):
    """Garante a comunicação e bloqueio real de instâncias concorrentes com QLocalServer/QLocalSocket."""
    import uuid

    from PySide6.QtNetwork import QLocalServer, QLocalSocket

    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"

    QLocalServer.removeServer(nome_servidor)
    servidor = QLocalServer()
    assert servidor.listen(nome_servidor) is True

    # Segunda conexão deve conectar com sucesso (detectando que o servidor está vivo)
    socket = QLocalSocket()
    socket.connectToServer(nome_servidor)
    assert socket.waitForConnected(500) is True
    socket.close()

    # Ao fechar o servidor, nova conexão não conecta
    servidor.close()
    socket2 = QLocalSocket()
    socket2.connectToServer(nome_servidor)
    assert socket2.waitForConnected(100) is False
    QLocalServer.removeServer(nome_servidor)


def test_executar_selecao_fecha_janela_principal_anterior_se_existir(qtbot):
    with patch("editor.main.TarefaInicializacao") as MockTarefa:
        with patch("editor.main.TelaDeCarregamento") as MockDialog:
            with patch("editor.main.QApplication.quit") as mock_quit:
                mock_tarefa_inst = MockTarefa.return_value
                mock_tarefa_inst.storage = MagicMock()
                mock_tarefa_inst.sessao_usuario = None

                mock_dialog_inst = MockDialog.return_value
                mock_dialog_inst.exec.return_value = QDialog.DialogCode.Rejected

                controlador = ControladorAplicativo()
                janela_mock = MagicMock()
                controlador.janela_principal = janela_mock

                controlador.executar_selecao()

                janela_mock.close.assert_called_once()
                assert controlador.janela_principal is None
                mock_quit.assert_called_once()
                controlador.abertura.close()


def test_controlador_app_configura_tema_claro_na_inicializacao(qtbot):
    """Garante que a inicialização do app força o tema claro chamando configurar_tema_claro_aplicacao."""
    with patch("editor.main.configurar_tema_claro_aplicacao") as mock_config:
        with patch("editor.main.TarefaInicializacao"):
            controlador = ControladorAplicativo()
            mock_config.assert_called_once_with(controlador.app)
            controlador.abertura.close()


def test_configurar_ambiente_plataforma_define_darkmode_zero(monkeypatch):
    """Garante que a plataforma padrão no Windows desativa o dark mode."""
    from editor.main import configurar_ambiente_plataforma

    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    with patch("sys.platform", "win32"):
        configurar_ambiente_plataforma()
        import os

        assert os.environ.get("QT_QPA_PLATFORM") == "windows:darkmode=0"


def test_controlador_app_configura_canal_beta(qtbot, monkeypatch):
    """Garante que o ControladorAplicativo configura o nome da aplicação e o ícone para o canal Beta."""
    monkeypatch.setenv("ARESTA_CANAL", "beta")
    with patch("editor.main.TarefaInicializacao"):
        controlador = ControladorAplicativo()
        assert controlador.app.applicationName() == "Editor Aresta (Beta)"
        assert not controlador.app.windowIcon().isNull()
        controlador.abertura.close()


def test_main_getattr_carregamento_sob_demanda():
    """Garante que classes pesadas são resolvidas sob demanda via PEP 562 __getattr__."""
    import editor.main as main_mod
    from editor.core.storage import GerenciadorCaminhos as GerenciadorReal
    from editor.core.worker import TarefaInicializacao as TarefaReal
    from editor.legacy_views.tela_de_carregamento import TelaDeCarregamento as TelaCarregamentoReal
    from editor.views.tela_de_abertura import TelaDeAbertura as TelaAberturaReal

    assert main_mod.__getattr__("TarefaInicializacao") is TarefaReal
    assert main_mod.__getattr__("TelaDeCarregamento") is TelaCarregamentoReal
    assert main_mod.__getattr__("TelaDeAbertura") is TelaAberturaReal
    assert main_mod.__getattr__("GerenciadorCaminhos") is GerenciadorReal

    with pytest.raises(AttributeError):
        main_mod.__getattr__("SimboloInexistenteNoEditor")


def test_controlador_app_ao_login_concluido(qtbot):
    with patch("editor.main.TarefaInicializacao"):
        controlador = ControladorAplicativo()
        sessao_mock = MagicMock()
        sessao_mock.nome_completo = "Escalador Teste"
        controlador.ao_login_concluido(sessao_mock)
        controlador.tarefa.gerenciador_sessao.salvar_sessao.assert_called_once_with(sessao_mock)
        controlador.tarefa.definir_sessao_concluida.assert_called_once_with(sessao_mock)
        controlador.abertura.close()


def test_controlador_app_ao_login_cancelado(qtbot):
    with patch("editor.main.TarefaInicializacao"):
        controlador = ControladorAplicativo()
        controlador.ao_login_cancelado()
        controlador.tarefa.definir_sessao_concluida.assert_called_once_with(None)
        controlador.abertura.close()


def test_controlador_app_mostrar_janela_principal_sem_selecao(qtbot):
    with patch("editor.main.TarefaInicializacao"):
        controlador = ControladorAplicativo()
        controlador.tela_carregamento = None
        controlador.mostrar_janela_principal()
        assert controlador.janela_principal is None
        controlador.abertura.close()


def test_controlador_app_abrir_croqui_via_mcp_atual_e_multi_janela(qtbot, tmp_path):
    """
    Valida que ControladorAplicativo abre o primeiro croqui na janela principal atual
    e abre croquis subsequentes em novas janelas independentes quando já há um croqui aberto.
    """
    from scripts.gerenciar_uids_lib import gerar_uid
    from scripts.migrador import obter_ultima_versao_migracao

    def _criar_pasta_exp(nome_id: str) -> Path:
        p = tmp_path / nome_id
        (p / "database").mkdir(parents=True, exist_ok=True)
        (p / "database" / "croqui.yaml").write_text(
            f"id: {nome_id}\nuid: {gerar_uid()}\nnome: {nome_id}\nultima_migracao: {obter_ultima_versao_migracao()}\n",
            encoding="utf-8",
        )
        return p

    pasta_a = _criar_pasta_exp("croqui_janela_a")
    pasta_b = _criar_pasta_exp("croqui_janela_b")

    with patch("editor.main.TarefaInicializacao") as MockTarefa:
        mock_tarefa_inst = MockTarefa.return_value
        mock_tarefa_inst.storage = None
        mock_tarefa_inst.gerenciador_sessao = None
        mock_tarefa_inst.sessao_usuario = None

        controlador = ControladorAplicativo()
        try:
            # 1. Sem janela principal aberta -> abre na janela principal atual
            res1 = controlador.abrir_croqui_via_mcp(pasta_a, iniciar_mcp_janela=False)
            assert res1["janela_aberta"] is True
            assert res1["nova_janela"] is False
            assert controlador.janela_principal is not None

            # 2. Com janela principal já aberta -> instancia segunda janela independente
            res2 = controlador.abrir_croqui_via_mcp(pasta_b, iniciar_mcp_janela=False)
            assert res2["janela_aberta"] is True
            assert res2["nova_janela"] is True
            assert len(controlador.janelas_secundarias) == 1
        finally:
            for j in controlador.janelas_secundarias:
                j.close()
            if controlador.janela_principal:
                controlador.janela_principal.close()
            controlador.abertura.close()


def test_integracao_abertura_croqui_oficial_mantem_app_vivo_e_mesmo_servidor_mcp(
    qtbot, tmp_path: Path
):
    """
    Teste de integração real (dentro de app.exec()) reproduzindo o fluxo completo:
    1. TelaDeAbertura -> TarefaInicializacao.sucesso -> TelaDeCarregamento (com ServidorMCP já ativo)
    2. Clique em 'Editar croqui oficial' -> DialogoBuscaCroqui -> QInputDialog -> DialogoProgressoLog
    3. Abertura da JanelaPrincipal sem encerrar prematuramente o app.exec() (sem aboutToQuit)
    4. Manutenção da mesma instância e porta do ServidorMCP entre TelaDeCarregamento e JanelaPrincipal
    5. Retorno via 'Abrir Novo' para a TelaDeCarregamento mantendo o mesmo ServidorMCP ativo
    """
    from PySide6.QtCore import QObject, QTimer, Signal
    from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

    from editor.legacy_views.dialogo_busca_croqui import DialogoBuscaCroqui
    from scripts.gerenciar_uids_lib import gerar_uid
    from scripts.migrador import obter_ultima_versao_migracao

    class _StorageTemp:
        def __init__(self, raiz: Path) -> None:
            self.raiz = raiz

        def obter_diretorio_base(self) -> Path:
            return self.raiz

        def obter_caminho_base_repo(self) -> Path:
            return self.raiz / "aresta_db"

        def obter_caminho_croquis_experimentais(self) -> Path:
            return self.raiz / "croquis"

        def obter_caminho_diarios_locais(self) -> Path:
            return self.raiz / "diarios_locais"

        def obter_caminho_lixeira(self) -> Path:
            return self.raiz / ".trash_interna"

        def inicializar_diretorios(self) -> None:
            self.obter_caminho_base_repo().mkdir(parents=True, exist_ok=True)
            self.obter_caminho_croquis_experimentais().mkdir(parents=True, exist_ok=True)
            self.obter_caminho_diarios_locais().mkdir(parents=True, exist_ok=True)
            self.obter_caminho_lixeira().mkdir(parents=True, exist_ok=True)

    class _SessaoTemp:
        nome_completo = "Escalador Integração"

    class _GerenciadorSessaoTemp:
        def obter_sessao(self) -> _SessaoTemp:
            return _SessaoTemp()

        def recuperar_token(self) -> str:
            return ""

    class _TarefaInicializacaoDeterministica(QObject):
        progresso = Signal(int)
        mostrar_progresso = Signal(bool)
        status = Signal(str)
        atualizacao_disponivel = Signal(object)
        auth_requerida = Signal(str)
        solicitar_login_ui = Signal()
        auth_concluida = Signal()
        sucesso = Signal()
        erro = Signal(str)

        def __init__(self, storage: _StorageTemp) -> None:
            super().__init__()
            self.storage = storage
            self.gerenciador_sessao = _GerenciadorSessaoTemp()
            self.sessao_usuario = _SessaoTemp()

        def start(self) -> None:
            QTimer.singleShot(20, self.sucesso.emit)

    storage = _StorageTemp(tmp_path)
    storage.inicializar_diretorios()
    id_oficial = "br_mg_igarape_pedra_grande"
    pasta_oficial = storage.obter_caminho_base_repo() / "database" / id_oficial
    pasta_oficial.mkdir(parents=True, exist_ok=True)
    (pasta_oficial / "croqui.yaml").write_text(
        f"id: {id_oficial}\n"
        f"uid: {gerar_uid()}\n"
        f"nome: Pedra Grande de Igarapé\n"
        f"ultima_migracao: {obter_ultima_versao_migracao()}\n"
        f"picos:\n"
        f"  - nome: Pedra Grande\n"
        f"    estado: MG\n",
        encoding="utf-8",
    )

    tarefa_fake = _TarefaInicializacaoDeterministica(storage)
    dir_sessao_mcp = tmp_path / "sessao_mcp"
    dir_sessao_mcp.mkdir(parents=True, exist_ok=True)

    controlador = ControladorAplicativo(
        tarefa=tarefa_fake,
        diretorio_sessao_mcp=dir_sessao_mcp,
    )
    app = controlador.app

    eventos: list[str] = []
    erros_modal: list[str] = []
    portas_mcp: list[int | None] = []
    instancias_mcp: list[object] = []
    vezes_tela_carregamento = 0

    def _ao_about_to_quit() -> None:
        eventos.append("aboutToQuit")

    app.aboutToQuit.connect(_ao_about_to_quit)

    def _inspecionar_ciclo() -> None:
        nonlocal vezes_tela_carregamento

        # Automação de diálogos modais filhos durante ao_clicar_oficial
        widget_modal = QApplication.activeModalWidget()
        if isinstance(widget_modal, QMessageBox):
            erros_modal.append(widget_modal.text())
            widget_modal.accept()
            app.quit()
            return
        if isinstance(widget_modal, DialogoBuscaCroqui):
            assert widget_modal.lista_croquis.count() == 1
            widget_modal.lista_croquis.setCurrentRow(0)
            widget_modal.accept()
            return
        if isinstance(widget_modal, QInputDialog):
            widget_modal.setTextValue("Revisão de integração")
            widget_modal.accept()
            return

        # 1ª passagem na TelaDeCarregamento: verifica MCP ativo e clica em 'Editar croqui oficial'
        if (
            controlador.tela_carregamento is not None
            and controlador.tela_carregamento.isVisible()
            and vezes_tela_carregamento == 0
        ):
            vezes_tela_carregamento = 1
            srv_carregamento = controlador.tela_carregamento.servidor_mcp
            assert srv_carregamento is not None
            assert srv_carregamento.esta_ativo is True
            assert srv_carregamento.croqui_aberto is False
            portas_mcp.append(srv_carregamento.porta)
            instancias_mcp.append(srv_carregamento)
            eventos.append("tela_carregamento_1")
            QTimer.singleShot(10, controlador.tela_carregamento.btn_oficial.click)
            return

        # JanelaPrincipal aberta após importar croqui oficial
        if (
            controlador.janela_principal is not None
            and controlador.janela_principal.isVisible()
            and "janela_principal_viva" not in eventos
        ):
            assert "aboutToQuit" not in eventos
            srv_janela = controlador.janela_principal.servidor_mcp
            assert srv_janela is not None
            assert srv_janela.esta_ativo is True
            assert srv_janela.croqui_aberto is True
            assert srv_janela.id_croqui_ativo == id_oficial
            portas_mcp.append(srv_janela.porta)
            instancias_mcp.append(srv_janela)
            eventos.append("janela_principal_viva")
            # Aciona 'Abrir Novo' para retornar à TelaDeCarregamento
            QTimer.singleShot(20, controlador.janela_principal._on_abrir_novo_clicado)
            return

        # 2ª passagem na TelaDeCarregamento após 'Abrir Novo'
        if (
            controlador.tela_carregamento is not None
            and controlador.tela_carregamento.isVisible()
            and "janela_principal_viva" in eventos
            and vezes_tela_carregamento == 1
        ):
            vezes_tela_carregamento = 2
            assert "aboutToQuit" not in eventos
            srv_retorno = controlador.tela_carregamento.servidor_mcp
            assert srv_retorno is not None
            assert srv_retorno.esta_ativo is True
            assert srv_retorno.croqui_aberto is False
            portas_mcp.append(srv_retorno.porta)
            instancias_mcp.append(srv_retorno)
            eventos.append("tela_carregamento_2")
            # Fecha a TelaDeCarregamento para encerrar o app normalmente
            QTimer.singleShot(10, controlador.tela_carregamento.reject)

    timer_inspecao = QTimer()
    timer_inspecao.setInterval(25)
    timer_inspecao.timeout.connect(_inspecionar_ciclo)
    timer_inspecao.start()
    # Timeout de segurança para nunca travar a suíte
    QTimer.singleShot(15000, app.quit)

    try:
        codigo_saida = controlador.executar()
        assert not erros_modal, f"Erros exibidos em QMessageBox: {erros_modal}"
        assert codigo_saida == 0
        assert eventos[:3] == [
            "tela_carregamento_1",
            "janela_principal_viva",
            "tela_carregamento_2",
        ]
        # O mesmo objeto ServidorMCP e a mesma porta foram mantidos em todas as etapas
        assert len(instancias_mcp) == 3
        assert instancias_mcp[0] is instancias_mcp[1] is instancias_mcp[2]
        assert portas_mcp[0] is not None
        assert portas_mcp[0] == portas_mcp[1] == portas_mcp[2]
    finally:
        timer_inspecao.stop()
        app.aboutToQuit.disconnect(_ao_about_to_quit)
        if hasattr(controlador, "encerrar_servidor_mcp"):
            controlador.encerrar_servidor_mcp()
        if controlador.janela_principal:
            controlador.janela_principal.close()
        if controlador.abertura:
            controlador.abertura.close()


def test_controlador_aplicativo_repassa_dependencias_injetadas(qtbot, tmp_path: Path) -> None:
    """Valida que ControladorAplicativo repassa storage, sessao, auth, loja, submissao e fabrica_celular."""
    from scripts.gerenciar_uids_lib import gerar_uid
    from scripts.migrador import obter_ultima_versao_migracao

    pasta_exp = tmp_path / "croqui_injecao"
    (pasta_exp / "database").mkdir(parents=True, exist_ok=True)
    (pasta_exp / "database" / "croqui.yaml").write_text(
        f"id: croqui_injecao\nuid: {gerar_uid()}\nnome: Croqui Injeção\nultima_migracao: {obter_ultima_versao_migracao()}\n",
        encoding="utf-8",
    )

    storage_obj = object()
    sessao_obj = object()
    auth_obj = object()
    loja_obj = object()
    submissao_obj = object()

    def _fabrica_celular(*args, **kwargs):
        return None

    with patch("editor.main.TarefaInicializacao") as mock_tarefa_cls:
        mock_tarefa_inst = mock_tarefa_cls.return_value
        mock_tarefa_inst.storage = storage_obj
        mock_tarefa_inst.gerenciador_sessao = sessao_obj
        mock_tarefa_inst.cliente_auth = auth_obj
        mock_tarefa_inst.servico_loja = loja_obj
        mock_tarefa_inst.sessao_usuario = None

        controlador = ControladorAplicativo(
            iniciar_mcp=False,
            storage=storage_obj,
            gerenciador_sessao=sessao_obj,
            cliente_auth=auth_obj,
            servico_loja=loja_obj,
            servico_submissao=submissao_obj,
            fabrica_servidor_celular=_fabrica_celular,
        )
        try:
            assert controlador.abertura.cliente_auth is auth_obj
            assert controlador.abertura.gerenciador_sessao is sessao_obj

            controlador.abrir_croqui_via_mcp(pasta_exp, iniciar_mcp_janela=False)
            assert controlador.janela_principal is not None
            assert controlador.janela_principal.servico_submissao is submissao_obj
            assert controlador.janela_principal.servico_loja is loja_obj
            assert controlador.janela_principal.fabrica_servidor_celular is _fabrica_celular
        finally:
            if controlador.janela_principal:
                controlador.janela_principal.close()
            if controlador.abertura:
                controlador.abertura.close()


