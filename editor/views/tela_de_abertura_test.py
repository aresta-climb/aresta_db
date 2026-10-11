# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt

from editor.core.cliente_auth_supabase import ErroAutenticacaoSupabase
from editor.plataforma import ResultadoAtualizacao, StatusAtualizacao
from editor.views.tela_de_abertura import TelaDeAbertura


@pytest.fixture
def mock_cliente_auth():
    cliente = MagicMock()
    cliente.solicitar_codigo_otp.return_value = True
    cliente.verificar_codigo_otp.return_value = {
        "access_token": "jwt-123",
        "refresh_token": "refresh-123",
        "user": {
            "id": "uuid-123",
            "email": "escalador@arestaclimb.com",
            "user_metadata": {"nome_completo": "Renato Utsch"},
        },
    }
    return cliente


def test_tela_abertura_componentes_iniciais(qtbot):
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    assert abertura.label_status.text() == "Iniciando..."
    assert not abertura.progress_bar.isVisible()
    assert not abertura.auth_container.isVisible()
    assert not abertura.update_container.isVisible()


def test_tela_abertura_exibir_barra_progresso(qtbot):
    abertura = TelaDeAbertura()
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.exibir_barra_progresso(True)
    assert abertura.progress_bar.isVisible()

    abertura.exibir_barra_progresso(False)
    assert not abertura.progress_bar.isVisible()


def test_tela_abertura_iniciar_fluxo_login_exibe_selecao(qtbot):
    abertura = TelaDeAbertura()
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()

    assert abertura.auth_container.isVisible()
    assert abertura.container_auth_selecao.isVisible()
    assert not abertura.container_auth_email.isVisible()
    assert not abertura.container_auth_codigo.isVisible()
    assert not abertura.label_status.isVisible()


def test_tela_abertura_transicao_para_formulario_email(qtbot):
    abertura = TelaDeAbertura()
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    qtbot.mouseClick(abertura.btn_escolher_email, Qt.MouseButton.LeftButton)

    assert not abertura.container_auth_selecao.isVisible()
    assert abertura.container_auth_email.isVisible()
    assert abertura.edit_email.text() == ""


def test_tela_abertura_solicitar_otp_transicao_para_codigo(qtbot, mock_cliente_auth):
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    abertura.mostrar_formulario_email()

    abertura.edit_email.setText("escalador@arestaclimb.com")
    abertura.solicitar_otp()
    qtbot.waitUntil(lambda: abertura.container_auth_codigo.isVisible(), timeout=2000)

    mock_cliente_auth.solicitar_codigo_otp.assert_called_once_with("escalador@arestaclimb.com")
    assert not abertura.container_auth_email.isVisible()
    assert abertura.container_auth_codigo.isVisible()
    assert "escalador@arestaclimb.com" in abertura.label_info_codigo.text()


def test_tela_abertura_validador_apenas_digitos(qtbot):
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    assert abertura.edit_codigo.maxLength() == 8
    assert abertura.edit_codigo.placeholderText() == ""
    assert abertura.label_info_codigo.textFormat() == Qt.TextFormat.RichText

    validator = abertura.edit_codigo.validator()
    assert validator is not None
    from PySide6.QtGui import QValidator

    assert validator.validate("12345678", 0)[0] == QValidator.State.Acceptable
    assert validator.validate("123abc", 0)[0] == QValidator.State.Invalid


def test_tela_abertura_validar_codigo_otp_8_digitos_sucesso(qtbot, mock_cliente_auth):
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    abertura.mostrar_formulario_email()
    abertura.edit_email.setText("escalador@arestaclimb.com")
    abertura.solicitar_otp()
    qtbot.waitUntil(lambda: abertura.container_auth_codigo.isVisible(), timeout=2000)

    abertura.edit_codigo.setText("12345678")

    with qtbot.waitSignal(abertura.login_concluido, timeout=2000) as bloqueador:
        abertura.validar_otp()

    sessao = bloqueador.args[0]
    assert sessao.email == "escalador@arestaclimb.com"
    assert sessao.nome_completo == "Renato Utsch"
    assert not abertura.auth_container.isVisible()
    assert abertura.label_status.isVisible()


def test_tela_abertura_voltar_para_selecao(qtbot):
    abertura = TelaDeAbertura()
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    abertura.mostrar_formulario_email()
    assert abertura.container_auth_email.isVisible()

    qtbot.mouseClick(abertura.btn_voltar_email, Qt.MouseButton.LeftButton)
    assert abertura.container_auth_selecao.isVisible()
    assert not abertura.container_auth_email.isVisible()


def test_tela_abertura_feedback_reenviar_codigo(qtbot, mock_cliente_auth):
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    abertura.mostrar_formulario_email()
    abertura.edit_email.setText("escalador@arestaclimb.com")
    abertura.solicitar_otp()
    qtbot.waitUntil(lambda: abertura.container_auth_codigo.isVisible(), timeout=2000)

    # Simula contagem zerando e reativando botão
    abertura._segundos_reenvio = 1
    abertura._atualizar_contador_reenvio()
    assert abertura.btn_reenviar_codigo.isEnabled()
    assert abertura.btn_reenviar_codigo.text() == "Reenviar código"

    # Clica em reenviar código e verifica feedback imediato
    abertura.solicitar_otp()
    assert not abertura.btn_reenviar_codigo.isEnabled()
    assert "Reenviando..." in abertura.btn_reenviar_codigo.text()

    qtbot.waitUntil(lambda: "Reenviar em" in abertura.btn_reenviar_codigo.text(), timeout=2000)


def test_tela_abertura_erro_solicitar_otp(qtbot, mock_cliente_auth):
    mock_cliente_auth.solicitar_codigo_otp.side_effect = ErroAutenticacaoSupabase("Rate limit")
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    abertura.mostrar_formulario_email()
    abertura.edit_email.setText("invalido@arestaclimb.com")

    with patch("PySide6.QtWidgets.QMessageBox.critical") as mock_erro:
        abertura.solicitar_otp()
        qtbot.waitUntil(lambda: mock_erro.called, timeout=2000)
        assert abertura.container_auth_email.isVisible()


def test_tela_abertura_botao_fechar(qtbot):
    with patch("editor.views.tela_de_abertura.QApplication.quit") as mock_quit:
        abertura = TelaDeAbertura()
        qtbot.addWidget(abertura)
        qtbot.mouseClick(abertura.btn_close, Qt.MouseButton.LeftButton)
        mock_quit.assert_called_once()


def test_tela_abertura_nao_fica_no_topo(qtbot):
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    flags = abertura.windowFlags()
    assert not (flags & Qt.WindowType.WindowStaysOnTopHint)
    assert flags & Qt.WindowType.FramelessWindowHint


def test_tela_abertura_logo_oficial(qtbot):
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    pixmap = abertura.label_logo.pixmap()
    assert pixmap is not None
    assert not pixmap.isNull()


def test_tela_abertura_logo_canal_beta(qtbot, monkeypatch):
    monkeypatch.setenv("ARESTA_CANAL", "beta")
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    pixmap = abertura.label_logo.pixmap()
    assert pixmap is not None
    assert not pixmap.isNull()
    assert abertura.windowTitle() == "Editor Aresta (Beta)"


def test_tela_abertura_exibir_aviso_atualizacao(qtbot):
    abertura = TelaDeAbertura()
    abertura.show()
    qtbot.addWidget(abertura)

    resultado = ResultadoAtualizacao(
        status=StatusAtualizacao.ATUALIZACAO_DISPONIVEL,
        versao_disponivel="1.5.0.0",
        mensagem="Nova versão disponível na Microsoft Store.",
    )

    mock_callback = MagicMock()
    abertura.exibir_aviso_atualizacao(resultado, callback_atualizar=mock_callback)

    assert abertura.update_container.isVisible()
    assert not abertura.label_status.isVisible()
    assert "1.5.0.0" in abertura.label_update_info.text()
    assert "Microsoft Store" not in abertura.label_update_info.text()
    assert "Editor Aresta" in abertura.label_update_info.text()

    qtbot.mouseClick(abertura.btn_atualizar_store, Qt.MouseButton.LeftButton)

    mock_callback.assert_called_once()

    abertura.esconder_aviso_atualizacao()
    assert not abertura.update_container.isVisible()


def test_tela_abertura_iniciar_login_github_configuracao_url(qtbot):
    abertura = TelaDeAbertura()
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()

    with patch("PySide6.QtGui.QDesktopServices.openUrl") as mock_open:
        abertura.iniciar_login_github()
        assert abertura.container_auth_github.isVisible()
        assert not abertura.container_auth_selecao.isVisible()

        mock_open.assert_called_once()
        url = mock_open.call_args[0][0].toString()
        assert "provider=github" in url
        assert "public_repo" in url
        assert "user%3Aemail" in url or "user:email" in url
        assert "redirect_to=http" in url
        assert "/callback" in url
        abertura.close()


def test_tela_abertura_fechamento_encerra_servidor_oauth(qtbot):
    abertura = TelaDeAbertura()
    abertura.show()
    qtbot.addWidget(abertura)

    with patch("PySide6.QtGui.QDesktopServices.openUrl"):
        abertura.iniciar_login_github()
        assert abertura.servidor_oauth is not None
        servidor = abertura.servidor_oauth

        abertura.close()
        assert abertura.servidor_oauth is None
        assert servidor._thread is None


def test_tela_abertura_login_github_retorna_erro_trata_e_volta_para_selecao(qtbot):
    abertura = TelaDeAbertura()
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    mock_servidor = MagicMock()
    abertura.servidor_oauth = mock_servidor

    with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_aviso:
        abertura._ao_receber_tokens_github({"erro": "access_denied"})
        mock_aviso.assert_called_once()
        assert abertura.container_auth_selecao.isVisible()
        assert not abertura.container_auth_github.isVisible()


def test_tela_abertura_drag_and_drop(qtbot):
    abertura = TelaDeAbertura()
    abertura.show()
    qtbot.addWidget(abertura)

    pos_inicial = abertura.pos()

    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent

    pos_local = QPointF(10.0, 10.0)
    pos_global = abertura.mapToGlobal(pos_local.toPoint())

    evento_press = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        pos_local,
        QPointF(pos_global.x(), pos_global.y()),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    abertura.mousePressEvent(evento_press)

    pos_global_movida = QPointF(pos_global.x() + 50, pos_global.y() + 50)
    pos_local_movida = QPointF(60.0, 60.0)

    evento_move = QMouseEvent(
        QEvent.Type.MouseMove,
        pos_local_movida,
        pos_global_movida,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    abertura.mouseMoveEvent(evento_move)

    nova_pos = abertura.pos()
    assert nova_pos.x() == pos_inicial.x() + 50
    assert nova_pos.y() == pos_inicial.y() + 50


def test_tela_abertura_solicitar_otp_com_cliente_padrao_chama_url_absoluta(
    qtbot,
):
    import responses

    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            "https://yzkhiaoqtxvvcyyuwmqg.supabase.co/auth/v1/otp",
            json={"message": "ok"},
            status=200,
        )
        abertura = TelaDeAbertura()
        abertura.show()
        qtbot.addWidget(abertura)

        abertura.iniciar_fluxo_login()
        abertura.mostrar_formulario_email()
        abertura.edit_email.setText("renatoutsch@gmail.com")
        abertura.solicitar_otp()

        qtbot.waitUntil(lambda: abertura.container_auth_codigo.isVisible(), timeout=3000)

        assert abertura.container_auth_codigo.isVisible()
        assert len(rsps.calls) == 1
        assert rsps.calls[0].request.url == "https://yzkhiaoqtxvvcyyuwmqg.supabase.co/auth/v1/otp"


def test_tela_abertura_define_titulo_e_configura_barra_de_tarefas(qtbot):
    with patch("editor.views.tela_de_abertura.configurar_presenca_barra_de_tarefas") as mock_config:
        abertura = TelaDeAbertura()
        qtbot.addWidget(abertura)

        assert abertura.windowTitle() == "Editor Aresta"
        mock_config.assert_called_once_with(int(abertura.winId()))


def test_tela_abertura_estilo_campos_entrada_fundo_claro(qtbot):
    """Garante que os campos de entrada definem fundo claro e cor de texto explícitos prevenindo preenchimento escuro no Linux."""
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    folha_email = abertura.edit_email.styleSheet().lower()
    assert "background-color" in folha_email
    assert "#ffffff" in folha_email
    assert "color:" in folha_email

    folha_codigo = abertura.edit_codigo.styleSheet().lower()
    assert "background-color" in folha_codigo
    assert "#ffffff" in folha_codigo
    assert "color:" in folha_codigo


def test_tela_abertura_janela_deslizante_permite_ate_6_envios(qtbot, mock_cliente_auth):
    """Valida que envios abaixo de 6 por minuto usam apenas cooldown curto (3s), sem bloquear por 60s."""
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    abertura.mostrar_formulario_email()
    abertura.edit_email.setText("escalador@arestaclimb.com")

    with patch("time.time", return_value=100.0):
        abertura.solicitar_otp()
        qtbot.waitUntil(lambda: abertura.container_auth_codigo.isVisible(), timeout=2000)

    # 1º envio: espera deve ser de apenas 3 segundos de cooldown
    assert abertura._segundos_reenvio == 3
    assert abertura.btn_reenviar_codigo.text() == "Reenviar em (3s)"
    assert len(abertura._historico_envios_otp) == 1

    # Simula passagem dos 3s
    for _ in range(3):
        abertura._atualizar_contador_reenvio()
    assert abertura.btn_reenviar_codigo.isEnabled()
    assert abertura.btn_reenviar_codigo.text() == "Reenviar código"


def test_tela_abertura_janela_deslizante_bloqueia_no_sexto_envio(qtbot, mock_cliente_auth):
    """Valida que ao atingir 6 envios em 60s, o botão bloqueia calculando o tempo até expirar o 1º envio."""
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    abertura.mostrar_formulario_email()
    abertura.edit_email.setText("escalador@arestaclimb.com")

    # Pré-popula 5 envios anteriores: t=10, 15, 20, 25, 30
    abertura._historico_envios_otp = [10.0, 15.0, 20.0, 25.0, 30.0]

    # Realiza o 6º envio no instante t=40.0
    with patch("time.time", return_value=40.0):
        abertura.solicitar_otp()
        qtbot.waitUntil(lambda: abertura.container_auth_codigo.isVisible(), timeout=2000)

    # O 1º envio foi aos 10.0s. Janela de 60s expira em: 60 - (40 - 10) = 30 segundos!
    assert len(abertura._historico_envios_otp) == 6
    assert abertura._segundos_reenvio == 30
    assert not abertura.btn_reenviar_codigo.isEnabled()
    assert abertura.btn_reenviar_codigo.text() == "Reenviar em (30s)"


def test_tela_abertura_janela_deslizante_limpeza_expirados(qtbot, mock_cliente_auth):
    """Valida que envios mais antigos que 60 segundos são descartados da janela deslizante."""
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    abertura.mostrar_formulario_email()
    abertura.edit_email.setText("escalador@arestaclimb.com")

    # 3 envios velhos (> 60s) e 2 recentes (< 60s)
    abertura._historico_envios_otp = [10.0, 20.0, 30.0, 80.0, 90.0]

    # Novo envio em t=100.0 (os envios em 10, 20 e 30 devem ser descartados)
    with patch("time.time", return_value=100.0):
        abertura.solicitar_otp()
        qtbot.waitUntil(lambda: abertura.container_auth_codigo.isVisible(), timeout=2000)

    # Sobram: 80.0, 90.0 e o novo 100.0 = 3 envios na janela
    assert abertura._historico_envios_otp == [80.0, 90.0, 100.0]
    # Como são 3 (< 6), cooldown padrão de 3s
    assert abertura._segundos_reenvio == 3
    assert abertura.btn_reenviar_codigo.text() == "Reenviar em (3s)"


def test_tela_abertura_banner_cofre_trancado_visivel_quando_cofre_indisponivel(qtbot):
    """Valida que o banner de aviso é exibido com o texto correto quando o cofre está indisponível."""
    mock_gerenciador = MagicMock()
    mock_gerenciador.cofre_disponivel.return_value = False

    abertura = TelaDeAbertura(gerenciador_sessao=mock_gerenciador)
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()

    assert not abertura.label_aviso_cofre.isHidden()
    assert (
        abertura.label_aviso_cofre.text()
        == "O cofre de senhas não foi desbloqueado. Você pode fazer login normalmente, mas sua sessão só será lembrada durante esta execução do app."
    )
    abertura.close()


def test_tela_abertura_banner_cofre_trancado_oculto_quando_cofre_disponivel(qtbot):
    """Valida que o banner de aviso fica oculto quando o cofre está disponível e operacional."""
    mock_gerenciador = MagicMock()
    mock_gerenciador.cofre_disponivel.return_value = True

    abertura = TelaDeAbertura(gerenciador_sessao=mock_gerenciador)
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()

    assert abertura.label_aviso_cofre.isHidden()
    abertura.close()


def test_tela_abertura_banner_cofre_trancado_parametro_explicito(qtbot):
    """Valida que o parâmetro cofre_disponivel em iniciar_fluxo_login controla a visibilidade."""
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login(cofre_disponivel=False)
    assert not abertura.label_aviso_cofre.isHidden()

    abertura.iniciar_fluxo_login(cofre_disponivel=True)
    assert abertura.label_aviso_cofre.isHidden()
    abertura.close()


def test_tela_abertura_banner_cofre_trancado_quando_cofre_disponivel_lanca_excecao(qtbot):
    """Valida que se cofre_disponivel() lançar exceção, o banner é exibido preventivamente."""
    mock_gerenciador = MagicMock()
    mock_gerenciador.cofre_disponivel.side_effect = RuntimeError("Erro de barramento")

    abertura = TelaDeAbertura(gerenciador_sessao=mock_gerenciador)
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    assert not abertura.label_aviso_cofre.isHidden()
    abertura.close()


def test_tela_abertura_banner_cofre_quando_gerenciador_sessao_none(qtbot):
    """Valida que quando gerenciador_sessao for None, o banner permanece oculto."""
    abertura = TelaDeAbertura(gerenciador_sessao=None)
    abertura.gerenciador_sessao = None
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    assert abertura.label_aviso_cofre.isHidden()
    abertura.close()


def test_tela_abertura_init_trata_excecao_ao_instanciar_gerenciador_sessao(qtbot):
    """Valida que se a instanciação do GerenciadorSessao falhar no __init__, define como None."""
    with patch(
        "editor.core.gerenciador_sessao.GerenciadorSessao", side_effect=Exception("Falha init")
    ):
        abertura = TelaDeAbertura()
        qtbot.addWidget(abertura)
        assert abertura.gerenciador_sessao is None
        abertura.close()


def test_tarefa_assincrona_executa_e_emite_sinais(qtbot):
    """Valida que TarefaAssincrona emite sucesso com retorno e erro quando exceção ocorre."""
    from editor.views.tela_de_abertura import TarefaAssincrona

    tarefa_ok = TarefaAssincrona(lambda x: x * 2, 21)
    with qtbot.waitSignal(tarefa_ok.sucesso, timeout=1000) as bloqueador_ok:
        tarefa_ok.run()
    assert bloqueador_ok.args[0] == 42

    def _falhar():
        raise ValueError("Erro assíncrono")

    tarefa_err = TarefaAssincrona(_falhar)
    with qtbot.waitSignal(tarefa_err.erro, timeout=1000) as bloqueador_err:
        tarefa_err.run()
    assert isinstance(bloqueador_err.args[0], ValueError)


def test_tela_abertura_atualizar_status_e_progresso(qtbot):
    """Valida métodos utilitários de atualização de texto de status e barra de progresso."""
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    abertura.atualizar_status("Carregando mapa...")
    assert abertura.label_status.text() == "Carregando mapa..."

    abertura.atualizar_progresso(75)
    assert abertura.progress_bar.value() == 75
    abertura.close()


def test_tela_abertura_voltar_para_selecao_encerra_servidor_oauth(qtbot):
    """Valida que voltar_para_selecao encerra qualquer servidor oauth ativo."""
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    mock_servidor = MagicMock()
    abertura.servidor_oauth = mock_servidor

    abertura.voltar_para_selecao()
    mock_servidor.encerrar.assert_called_once()
    assert abertura.servidor_oauth is None
    abertura.close()


def test_tela_abertura_solicitar_otp_email_invalido(qtbot):
    """Valida que e-mails vazios ou sem '@' exibem aviso e não disparam tarefa assíncrona."""
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_aviso:
        abertura.edit_email.setText("emailinvalido")
        abertura.solicitar_otp()
        mock_aviso.assert_called_once()

    with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_aviso:
        abertura.edit_email.setText("   ")
        abertura.solicitar_otp()
        mock_aviso.assert_called_once()
    abertura.close()


def test_tela_abertura_validar_otp_codigo_tamanho_invalido(qtbot):
    """Valida que código com tamanho fora do intervalo (6 a 8 dígitos) exibe aviso."""
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_aviso:
        abertura.edit_codigo.setText("123")
        abertura.validar_otp()
        mock_aviso.assert_called_once()
    abertura.close()


def test_tela_abertura_ao_erro_validar_otp(qtbot):
    """Valida que falha na validação do OTP exibe mensagem crítica e reabilita o botão."""
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    with patch("PySide6.QtWidgets.QMessageBox.critical") as mock_critico:
        abertura._ao_erro_validar_otp(ValueError("Código expirado"))
        mock_critico.assert_called_once()
        assert abertura.btn_validar_codigo.isEnabled()
    abertura.close()


def test_tela_abertura_validar_otp_solicita_nome_completo_quando_incompleto(qtbot, mock_cliente_auth):
    """Valida fluxo em que OTP tem sucesso mas exige diálogo de perfil do autor."""
    from PySide6.QtWidgets import QDialog

    mock_cliente_auth.verificar_codigo_otp.return_value = {
        "access_token": "jwt-abc",
        "refresh_token": "refresh-abc",
        "user": {
            "id": "uuid-abc",
            "email": "escalador@arestaclimb.com",
            "user_metadata": {"nome_completo": "Renato"},
        },
    }
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    qtbot.addWidget(abertura)
    abertura._email_atual = "escalador@arestaclimb.com"

    with (
        patch("editor.views.tela_de_abertura.DialogoPerfilAutor") as mock_dialogo_cls,
        qtbot.waitSignal(abertura.login_concluido, timeout=2000) as bloqueador,
    ):
        mock_instancia = mock_dialogo_cls.return_value
        mock_instancia.exec.return_value = QDialog.DialogCode.Accepted
        mock_instancia.obter_nome_completo.return_value = "Renato Utsch"

        abertura._ao_sucesso_validar_otp(mock_cliente_auth.verificar_codigo_otp.return_value)

    sessao = bloqueador.args[0]
    assert sessao.nome_completo == "Renato Utsch"
    mock_cliente_auth.atualizar_nome_autor.assert_called_once_with("jwt-abc", "Renato Utsch")
    abertura.close()


def test_tela_abertura_validar_otp_dialogo_perfil_rejeitado_cancela(qtbot, mock_cliente_auth):
    """Valida que se o diálogo de perfil for cancelado, a validação de OTP é abortada."""
    from PySide6.QtWidgets import QDialog

    dados = {
        "access_token": "jwt-abc",
        "refresh_token": "refresh-abc",
        "user": {
            "id": "uuid-abc",
            "email": "escalador@arestaclimb.com",
            "user_metadata": {"nome_completo": "ApenasNome"},
        },
    }
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    qtbot.addWidget(abertura)

    with patch("editor.views.tela_de_abertura.DialogoPerfilAutor") as mock_dialogo_cls:
        mock_instancia = mock_dialogo_cls.return_value
        mock_instancia.exec.return_value = QDialog.DialogCode.Rejected
        abertura._ao_sucesso_validar_otp(dados)

    mock_cliente_auth.atualizar_nome_autor.assert_not_called()
    abertura.close()


def test_tela_abertura_validar_otp_trata_excecao_ao_atualizar_nome(qtbot, mock_cliente_auth):
    """Valida que falha no Supabase ao persistir nome completo não aborta a sessão."""
    from PySide6.QtWidgets import QDialog

    mock_cliente_auth.atualizar_nome_autor.side_effect = RuntimeError("Erro Supabase")
    dados = {
        "access_token": "jwt-abc",
        "refresh_token": "refresh-abc",
        "user": {
            "id": "uuid-abc",
            "email": "escalador@arestaclimb.com",
            "user_metadata": {"nome_completo": ""},
        },
    }
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    qtbot.addWidget(abertura)

    with (
        patch("editor.views.tela_de_abertura.DialogoPerfilAutor") as mock_dialogo_cls,
        qtbot.waitSignal(abertura.login_concluido, timeout=2000) as bloqueador,
    ):
        mock_instancia = mock_dialogo_cls.return_value
        mock_instancia.exec.return_value = QDialog.DialogCode.Accepted
        mock_instancia.obter_nome_completo.return_value = "Renato Utsch"

        abertura._ao_sucesso_validar_otp(dados)

    assert bloqueador.args[0].nome_completo == "Renato Utsch"
    abertura.close()


def test_tela_abertura_receber_tokens_github_vazio_ou_tipo_invalido(qtbot):
    """Valida que tokens inválidos ou vazios são ignorados em _ao_receber_tokens_github."""
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    abertura._ao_receber_tokens_github(None)
    abertura._ao_receber_tokens_github([])
    abertura._ao_receber_tokens_github("")
    abertura.close()


def test_tela_abertura_receber_tokens_github_sucesso_com_nome_completo(qtbot, mock_cliente_auth):
    """Valida login bem-sucedido com GitHub quando o perfil já contém nome completo."""
    mock_cliente_auth.obter_usuario_atual.return_value = {
        "email": "github@arestaclimb.com",
        "user_metadata": {"nome_completo": "Renato Utsch"},
    }
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    qtbot.addWidget(abertura)

    tokens = {
        "access_token": "gh-jwt-123",
        "refresh_token": "gh-refresh-123",
        "provider_token": "gh-pat-123",
    }

    with qtbot.waitSignal(abertura.login_concluido, timeout=2000) as bloqueador:
        abertura._ao_receber_tokens_github(tokens)

    sessao = bloqueador.args[0]
    assert sessao.email == "github@arestaclimb.com"
    assert sessao.nome_completo == "Renato Utsch"
    assert sessao.token_github == "gh-pat-123"
    abertura.close()


def test_tela_abertura_receber_tokens_github_sucesso_com_dialogo_perfil(qtbot, mock_cliente_auth):
    """Valida login GitHub que solicita nome completo via diálogo de perfil."""
    from PySide6.QtWidgets import QDialog

    mock_cliente_auth.obter_usuario_atual.return_value = {
        "email": "github@arestaclimb.com",
        "user_metadata": {"full_name": "Renato"},
    }
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    qtbot.addWidget(abertura)

    tokens = {
        "access_token": "gh-jwt-456",
        "refresh_token": "gh-refresh-456",
    }

    with (
        patch("editor.views.tela_de_abertura.DialogoPerfilAutor") as mock_dialogo_cls,
        qtbot.waitSignal(abertura.login_concluido, timeout=2000) as bloqueador,
    ):
        mock_instancia = mock_dialogo_cls.return_value
        mock_instancia.exec.return_value = QDialog.DialogCode.Accepted
        mock_instancia.obter_nome_completo.return_value = "Renato Utsch"

        abertura._ao_receber_tokens_github(tokens)

    sessao = bloqueador.args[0]
    assert sessao.nome_completo == "Renato Utsch"
    mock_cliente_auth.atualizar_nome_autor.assert_called_once_with("gh-jwt-456", "Renato Utsch")
    abertura.close()


def test_tela_abertura_receber_tokens_github_trata_excecao_ao_atualizar_nome(qtbot, mock_cliente_auth):
    """Valida que falha no Supabase ao atualizar nome do autor no GitHub é tratada graciosamente."""
    from PySide6.QtWidgets import QDialog

    mock_cliente_auth.obter_usuario_atual.return_value = {
        "email": "github@arestaclimb.com",
        "user_metadata": {"full_name": "Renato"},
    }
    mock_cliente_auth.atualizar_nome_autor.side_effect = RuntimeError("Erro Supabase")
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    qtbot.addWidget(abertura)

    tokens = {"access_token": "gh-jwt-456"}

    with (
        patch("editor.views.tela_de_abertura.DialogoPerfilAutor") as mock_dialogo_cls,
        qtbot.waitSignal(abertura.login_concluido, timeout=2000) as bloqueador,
    ):
        mock_instancia = mock_dialogo_cls.return_value
        mock_instancia.exec.return_value = QDialog.DialogCode.Accepted
        mock_instancia.obter_nome_completo.return_value = "Renato Utsch"

        abertura._ao_receber_tokens_github(tokens)

    sessao = bloqueador.args[0]
    assert sessao.nome_completo == "Renato Utsch"
    abertura.close()


def test_tela_abertura_receber_tokens_github_dialogo_perfil_cancelado(qtbot, mock_cliente_auth):
    """Valida cancelamento do login GitHub quando usuário rejeita o diálogo de perfil."""
    from PySide6.QtWidgets import QDialog

    mock_cliente_auth.obter_usuario_atual.return_value = {
        "email": "github@arestaclimb.com",
        "user_metadata": {},
    }
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    qtbot.addWidget(abertura)

    tokens = {"access_token": "gh-jwt-789"}

    with patch("editor.views.tela_de_abertura.DialogoPerfilAutor") as mock_dialogo_cls:
        mock_instancia = mock_dialogo_cls.return_value
        mock_instancia.exec.return_value = QDialog.DialogCode.Rejected
        abertura._ao_receber_tokens_github(tokens)

    assert not abertura.container_auth_selecao.isHidden()
    abertura.close()


def test_tela_abertura_receber_tokens_github_trata_excecao_obter_usuario(qtbot, mock_cliente_auth):
    """Valida que exceção ao obter usuário do Supabase no login GitHub é capturada sem crash."""
    from PySide6.QtWidgets import QDialog

    mock_cliente_auth.obter_usuario_atual.side_effect = RuntimeError("Erro Supabase")
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    qtbot.addWidget(abertura)

    tokens = {"access_token": "gh-jwt-000"}

    with (
        patch("editor.views.tela_de_abertura.DialogoPerfilAutor") as mock_dialogo_cls,
        qtbot.waitSignal(abertura.login_concluido, timeout=2000),
    ):
        mock_instancia = mock_dialogo_cls.return_value
        mock_instancia.exec.return_value = QDialog.DialogCode.Accepted
        mock_instancia.obter_nome_completo.return_value = "Renato Utsch"

        abertura._ao_receber_tokens_github(tokens)
    abertura.close()


def test_tela_abertura_cancelar_login_github(qtbot):
    """Valida que cancelar_login_github encerra servidor oauth e retorna para seleção."""
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)

    mock_servidor = MagicMock()
    abertura.servidor_oauth = mock_servidor

    abertura.cancelar_login_github()
    mock_servidor.encerrar.assert_called_once()
    assert abertura.servidor_oauth is None
    assert not abertura.container_auth_selecao.isHidden()

    # Testa também quando servidor_oauth for None
    abertura.cancelar_login_github()
    assert not abertura.container_auth_selecao.isHidden()
    abertura.close()
