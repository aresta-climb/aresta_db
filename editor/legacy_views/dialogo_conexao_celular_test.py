# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from editor.core.servidor_celular_fake import ServidorCelularFake
from editor.legacy_views.dialogo_conexao_celular import DialogoConexaoCelular


@pytest.fixture
def dialogo(qtbot, tmp_path: Path):
    servidor = ServidorCelularFake(tmp_path, codigo_sessao="k9x2p83a")
    servidor.iniciar()
    dlg = DialogoConexaoCelular(servidor)
    qtbot.addWidget(dlg)
    yield dlg
    dlg.close()


def test_deve_exibir_endereco_codigo_e_qr_code_carregados(qtbot, dialogo):
    """Aguarda a tarefa de background emitir a URL canônica, código formatado e QR Code."""
    qtbot.wait_until(
        lambda: dialogo.label_endereco.text() == "http://127.0.0.1:8765/k9x2p83a",
        timeout=2000,
    )
    assert dialogo.label_codigo.text() == "k9x2-p83a"
    assert dialogo.label_qr.pixmap() is not None


def test_deve_mudar_status_quando_conectado(qtbot, dialogo):
    """Muda o rótulo de status quando o sinal de conexão for disparado."""
    qtbot.wait_until(
        lambda: not dialogo.label_endereco.text().startswith("Aguardando"), timeout=2000
    )

    dialogo.servidor.simular_conexao_dispositivo()
    assert dialogo.label_status.text() == "Celular Conectado!"


def test_deve_copiar_url_para_clipboard(qtbot, dialogo):
    """Copia a URL canônica para o clipboard do sistema."""
    qtbot.wait_until(
        lambda: not dialogo.label_endereco.text().startswith("Aguardando"), timeout=2000
    )
    url = dialogo.label_endereco.text()

    qtbot.mouseClick(dialogo.btn_copiar, Qt.MouseButton.LeftButton)

    cb = QGuiApplication.clipboard()
    assert cb.text() == url


def test_deve_emitir_sinal_ao_clicar_encerrar(qtbot, dialogo):
    """Emite solicitar_encerrar ao clicar no botão encerrar."""
    with qtbot.wait_signal(dialogo.solicitar_encerrar):
        qtbot.mouseClick(dialogo.btn_encerrar, Qt.MouseButton.LeftButton)


def test_fechar_dialogo_encerra_e_aguarda_tarefa_dados_em_andamento(qtbot, tmp_path: Path):
    """Garante que fechar ou rejeitar o diálogo cancela cooperativamente e aguarda TarefaDadosConexao terminar."""
    servidor_lento = ServidorCelularFake(tmp_path, codigo_sessao="k9x2p83a")
    # Porta permanece None para manter TarefaDadosConexao aguardando em background
    dlg = DialogoConexaoCelular(servidor_lento)
    qtbot.addWidget(dlg)

    qtbot.wait_until(lambda: dlg.tarefa_dados.isRunning(), timeout=1000)
    dlg.reject()

    assert not dlg.tarefa_dados.isRunning()


def test_deve_exibir_erro_quando_tarefa_dados_falha(qtbot, tmp_path: Path):
    """Exibe erro explícito na UI e mantém QR Code oculto quando a criação da sessão de prévia falha."""
    servidor_erro = ServidorCelularFake(
        tmp_path,
        erro_previa=RuntimeError(
            "Não foi possível iniciar sessão de prévia. Verifique sua autenticação."
        ),
    )
    servidor_erro.iniciar()
    dlg = DialogoConexaoCelular(servidor_erro)
    qtbot.addWidget(dlg)
    try:
        qtbot.wait_until(
            lambda: "sessão de prévia" in dlg.label_status.text(),
            timeout=2000,
        )
        assert not dlg.widget_carregando.isVisible()
        assert not dlg.label_qr.isVisible()
        assert dlg.label_endereco.text().startswith("Indisponível")

        # Clicar em copiar quando indisponível não deve alterar o clipboard
        cb = QGuiApplication.clipboard()
        cb.setText("preservado")
        qtbot.mouseClick(dlg.btn_copiar, Qt.MouseButton.LeftButton)
        assert cb.text() == "preservado"
    finally:
        dlg.close()
