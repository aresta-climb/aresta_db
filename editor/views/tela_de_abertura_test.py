# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from unittest.mock import MagicMock, patch

from editor.views.tela_de_abertura import TelaDeAbertura
from editor.core.servico_loja import ResultadoAtualizacao, StatusAtualizacao
from editor.core.gerenciador_sessao import SessaoUsuario
from editor.core.cliente_auth_supabase import ErroAutenticacaoSupabase


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


def test_tela_abertura_solicitar_otp_transicao_para_codigo(
    qtbot, mock_cliente_auth
):
    abertura = TelaDeAbertura(cliente_auth=mock_cliente_auth)
    abertura.show()
    qtbot.addWidget(abertura)

    abertura.iniciar_fluxo_login()
    abertura.mostrar_formulario_email()

    abertura.edit_email.setText("escalador@arestaclimb.com")
    abertura.solicitar_otp()
    qtbot.waitUntil(lambda: abertura.container_auth_codigo.isVisible(), timeout=2000)

    mock_cliente_auth.solicitar_codigo_otp.assert_called_once_with(
        "escalador@arestaclimb.com"
    )
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


def test_tela_abertura_validar_codigo_otp_8_digitos_sucesso(
    qtbot, mock_cliente_auth
):
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

    qtbot.waitUntil(
        lambda: "Reenviar em" in abertura.btn_reenviar_codigo.text(), timeout=2000
    )


def test_tela_abertura_erro_solicitar_otp(qtbot, mock_cliente_auth):
    mock_cliente_auth.solicitar_codigo_otp.side_effect = (
        ErroAutenticacaoSupabase("Rate limit")
    )
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

    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import QPointF, QEvent

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
