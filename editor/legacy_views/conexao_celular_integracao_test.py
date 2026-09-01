# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
import requests
import time
from PySide6.QtWidgets import QApplication
from editor.legacy_views.dialogo_conexao_celular import DialogoConexaoCelular
from editor.core.servidor_celular import ServidorCelular
from pathlib import Path

@pytest.fixture
def integracao(tmp_path, qtbot):
    """Fixture que prepara o ambiente de integração com servidor real e diálogo."""
    pasta = tmp_path / "compilado"
    pasta.mkdir()
    (pasta / "indice.binarypb").write_text("fake_pb_data", encoding="utf-8")
    
    servidor = ServidorCelular(str(pasta))
    servidor.iniciar()
    
    dialogo = DialogoConexaoCelular(servidor)
    qtbot.addWidget(dialogo)
    
    # Aguarda o servidor estar pronto (IP e Porta descobertos e mostrados na UI)
    qtbot.wait_until(lambda: not dialogo.label_endereco.text().startswith("Aguardando"), timeout=5000)
    
    yield dialogo, servidor
    
    # Teardown
    servidor.parar()
    if servidor._thread_servidor and servidor._thread_servidor.is_alive():
        servidor._thread_servidor.join(timeout=3.0)


def test_status_deve_mudar_para_conectado_ao_receber_get_real(qtbot, integracao):
    """
    Simula uma requisição GET real ao servidor e verifica se a UI do diálogo
    reage mudando o status para 'Celular Conectado!'.
    """
    dialogo, servidor = integracao
    url_base = f"http://127.0.0.1:{servidor.porta}"
    
    url_arquivo = f"{url_base}/indice.binarypb"
    resposta = requests.get(url_arquivo, timeout=2)
    
    assert resposta.status_code == 200
    assert resposta.text == "fake_pb_data"
    
    qtbot.wait_until(lambda: dialogo.label_status.text() == "Celular Conectado!", timeout=2000)
    
    from editor.views.estilo import Icones
    assert Icones.COR_SUCESSO.lower() in dialogo.label_status.styleSheet().lower()


def test_listagem_de_diretorio_deve_funcionar_na_integracao(integracao, qtbot):
    """
    Tenta acessar o endpoint /handshake no servidor local e verifica se:
    1. O servidor retorna 200.
    2. O status da UI muda para 'Celular Conectado!'.
    """
    dialogo, servidor = integracao
    url_base = f"http://127.0.0.1:{servidor.porta}"
    
    resposta = requests.get(f"{url_base}/handshake", timeout=2)
    
    assert resposta.status_code == 200
    
    qtbot.wait_until(lambda: dialogo.label_status.text() == "Celular Conectado!", timeout=2000)


def test_parar_servidor_deve_ser_rapido_e_limpo(integracao, qtbot):
    """
    Valida se o método parar() realmente encerra o servidor e não bloqueia a UI.
    """
    dialogo, servidor = integracao
    
    assert servidor._servindo is True
    
    inicio = time.time()
    servidor.parar()
    fim = time.time()
    
    assert (fim - inicio) < 0.2
    
    def servidor_parou():
        return servidor._servindo is False
        
    qtbot.wait_until(servidor_parou, timeout=3000)
    assert servidor._servindo is False
