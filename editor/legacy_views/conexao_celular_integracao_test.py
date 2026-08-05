# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
import requests
import time
from PyQt6.QtWidgets import QApplication
from editor.legacy_views.dialogo_conexao_celular import DialogoConexaoCelular
from editor.core.servidor_celular import ServidorCelular
from pathlib import Path

@pytest.fixture
def integracao(tmp_path, qtbot):
    """Fixture que prepara o ambiente de integração com servidor real e diálogo."""
    # Pasta temporária para o servidor simular arquivos compilados
    pasta = tmp_path / "compilado"
    pasta.mkdir()
    (pasta / "indice.binarypb").write_text("fake_pb_data", encoding="utf-8")
    
    # O ServidorCelular real será usado e deve ser iniciado explicitamente
    servidor = ServidorCelular(str(pasta))
    servidor.iniciar()
    
    # O diálogo inicia a tarefa de background que aguarda o servidor estar pronto
    dialogo = DialogoConexaoCelular(servidor)
    qtbot.addWidget(dialogo)
    
    # Aguarda o servidor estar pronto (IP e Porta descobertos e mostrados na UI)
    # Isso garante que a thread do servidor subiu
    qtbot.wait_until(lambda: dialogo.label_endereco.text().startswith("http"), timeout=5000)
    
    yield dialogo, servidor
    
    # Limpeza
    servidor.parar()

def test_status_deve_mudar_para_conectado_ao_receber_get_real(qtbot, integracao):
    """
    Simula uma requisição GET real ao servidor e verifica se a UI do diálogo
    reage mudando o status para 'Conectado!'.
    """
    dialogo, servidor = integracao
    url_base = dialogo.label_endereco.text()
    
    # Realiza uma requisição HTTP real ao servidor que está rodando em background
    # Usamos o caminho de um arquivo que sabemos que existe
    url_arquivo = f"{url_base}/indice.binarypb"
    resposta = requests.get(url_arquivo, timeout=2)
    
    assert resposta.status_code == 200
    assert resposta.text == "fake_pb_data"
    
    # Verifica se a UI reagiu ao sinal emitido pelo servidor
    # O servidor deve emitir dispositivo_conectado em qualquer GET
    qtbot.wait_until(lambda: dialogo.label_status.text() == "Conectado!", timeout=2000)
    
    # Verifica também a cor do status (usando a constante definida em Icones)
    from editor.views.estilo import Icones
    assert Icones.COR_SUCESSO.lower() in dialogo.label_status.styleSheet().lower()

def test_listagem_de_diretorio_deve_funcionar_na_integracao(integracao, qtbot):
    """
    Tenta acessar a raiz do servidor (listagem de diretório) e verifica se:
    1. O servidor retorna 200 (listagem de diretório habilitada).
    2. O status da UI muda para 'Conectado!'.
    """
    dialogo, servidor = integracao
    url_base = dialogo.label_endereco.text()
    
    # Tenta acessar a rota /handshake para confirmar conexão
    resposta = requests.get(f"{url_base}/handshake", timeout=2)
    
    assert resposta.status_code == 200
    
    # O status deve mudar para "Conectado!"
    qtbot.wait_until(lambda: dialogo.label_status.text() == "Conectado!", timeout=2000)

def test_parar_servidor_deve_ser_rapido_e_limpo(integracao, qtbot):
    """
    Valida se o método parar() realmente encerra o servidor e não bloqueia a UI.
    """
    dialogo, servidor = integracao
    
    # O servidor deve estar rodando
    assert servidor._servindo is True
    
    # Chama o encerramento
    import time
    inicio = time.time()
    servidor.parar()
    fim = time.time()
    
    # O método parar() agora é assíncrono, deve retornar quase instantaneamente (< 0.2s)
    # Anteriormente o join(1.0) causava um atraso perceptível
    assert (fim - inicio) < 0.2
    
    # Mas queremos saber se ele REALMENTE parou por baixo dos panos
    # Esperamos um pouco para a thread de shutdown terminar
    def servidor_parou():
        return servidor._servindo is False
        
    qtbot.wait_until(servidor_parou, timeout=5000)
    assert servidor._servindo is False
