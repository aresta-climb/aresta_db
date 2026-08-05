# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import sys
from pathlib import Path
from unittest.mock import patch, mock_open
import io

# Adiciona o diretório raiz ao sys.path para garantir que imports funcionem nos testes também
sys.path.append(str(Path(__file__).resolve().parent.parent))

from aresta_api.proto.generated import croqui_pb2
from scripts.verificar_binarypb import verify_pb

def test_verificacao_de_pb(capsys):
    # Cria uma estrutura fictícia
    croqui = croqui_pb2.Croqui(
        id="br_mg_bh",
        nome="Belo Horizonte",
    )
    pico = croqui.picos.add(nome="Serra do Curral")
    bot = croqui.botoes.add(texto="Capa")
    bot.destino.secao_textual.conteudo = "# Capa"
    elemento = pico.setores_ou_grupos.add()
    elemento.setor.conteudo.nome = "Setor Ficticio"
    
    escalada = elemento.setor.conteudo.escaladas.add()
    escalada.via_esportiva.nome = "Toca"
    escalada.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_5SUP
    
    serialized_data = croqui.SerializeToString()
    
    # Mock do 'open' function
    m = mock_open(read_data=serialized_data)
    with patch("builtins.open", m):
        verify_pb("fake_file.binarypb")
        
    # Verifica o output impresso pelo verify_pb
    captured = capsys.readouterr()
    assert "Lendo fake_file.binarypb..." in captured.out
    assert "ID: br_mg_bh" in captured.out
    assert "Nome: Belo Horizonte" in captured.out
    assert "Botões: 1" in captured.out
    assert "Pico: Serra do Curral" in captured.out
    assert "Setor 1: Setor Ficticio (1 escaladas)" in captured.out
    assert "Primeira via: Toca (Grau: 11)" in captured.out

    # Verifica se abriu corretamente para leitura binária
    m.assert_called_once_with("fake_file.binarypb", "rb")
