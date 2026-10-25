# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import socket
from pathlib import Path

from editor.core.storage import obter_diretorio_base_app
from editor.mcp.sessao import (
    NOME_ARQUIVO_SESSAO_MCP,
    PORTA_MCP_PADRAO,
    alocar_porta_mcp,
    descobrir_url_mcp_ativa,
    gravar_sessao_mcp,
    ler_sessao_mcp,
    obter_caminho_sessao_mcp,
    porta_disponivel_local,
    remover_sessao_mcp,
)


def test_obter_caminho_sessao_padrao_e_customizado(tmp_path: Path):
    """Deve retornar o caminho no diretório base do app por padrão ou no diretório informado."""
    caminho_padrao = obter_caminho_sessao_mcp()
    assert caminho_padrao == obter_diretorio_base_app() / NOME_ARQUIVO_SESSAO_MCP

    caminho_custom = obter_caminho_sessao_mcp(tmp_path)
    assert caminho_custom == tmp_path / NOME_ARQUIVO_SESSAO_MCP


def test_alocar_porta_mcp_com_fallback_quando_ocupada():
    """Quando a porta preferencial estiver ocupada em 127.0.0.1, deve alocar a próxima porta livre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_ocupado:
        sock_ocupado.bind(("127.0.0.1", 0))
        sock_ocupado.listen(1)
        porta_ocupada = int(sock_ocupado.getsockname()[1])

        assert porta_disponivel_local(porta_ocupada) is False

        porta_alocada = alocar_porta_mcp(porta_preferencial=porta_ocupada)
        assert porta_alocada != porta_ocupada
        assert porta_alocada > 0
        assert porta_disponivel_local(porta_alocada) is True

        # Fallback para porta efêmera do SO quando o intervalo sequencial está esgotado
        porta_efemera = alocar_porta_mcp(
            porta_preferencial=porta_ocupada, max_tentativas_sequenciais=1
        )
        assert porta_efemera != porta_ocupada
        assert porta_efemera > 0


def test_alocar_porta_mcp_respeita_variavel_de_ambiente():
    """Quando porta_preferencial não é informada, deve respeitar ARESTA_MCP_PORTA se válida."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        porta_livre = int(s.getsockname()[1])

    porta_via_env = alocar_porta_mcp(env={"ARESTA_MCP_PORTA": str(porta_livre)})
    assert porta_via_env == porta_livre

    # Valor inválido no ambiente deve usar a porta padrão 27378 (ou seguinte livre)
    porta_padrao_ou_seguinte = alocar_porta_mcp(env={"ARESTA_MCP_PORTA": "invalida"})
    assert porta_padrao_ou_seguinte >= PORTA_MCP_PADRAO


def test_persistencia_ciclo_vida_sessao_mcp(tmp_path: Path):
    """Deve gravar, ler e remover o arquivo mcp_sessao.json corretamente."""
    assert ler_sessao_mcp(tmp_path) is None

    sessao = gravar_sessao_mcp(porta=27378, diretorio_base=tmp_path)
    assert sessao.porta == 27378
    assert sessao.pid > 0
    assert len(sessao.token) >= 16
    assert sessao.url_http == "http://127.0.0.1:27378/mcp"
    assert sessao.url_sse == "http://127.0.0.1:27378/mcp/sse"

    lida = ler_sessao_mcp(tmp_path)
    assert lida is not None
    assert lida.porta == 27378
    assert lida.pid == sessao.pid
    assert lida.token == sessao.token
    assert lida.url_http == sessao.url_http
    assert lida.url_sse == sessao.url_sse

    remover_sessao_mcp(tmp_path)
    assert ler_sessao_mcp(tmp_path) is None


def test_ler_sessao_mcp_arquivo_corrompido(tmp_path: Path):
    """Se o arquivo mcp_sessao.json estiver corrompido ou sem porta válida, deve retornar None."""
    caminho = obter_caminho_sessao_mcp(tmp_path)
    caminho.write_text("{json_invalido", encoding="utf-8")
    assert ler_sessao_mcp(tmp_path) is None

    caminho.write_text('{"sem_porta": true}', encoding="utf-8")
    assert ler_sessao_mcp(tmp_path) is None


def test_descobrir_url_mcp_ativa_prioridades(tmp_path: Path):
    """Deve priorizar ARESTA_MCP_PORTA, depois mcp_sessao.json e por fim o fallback 27378."""
    # 1. Sem arquivo e sem env -> fallback para PORTA_MCP_PADRAO (27378)
    url, token = descobrir_url_mcp_ativa(diretorio_base=tmp_path, env={})
    assert url == f"http://127.0.0.1:{PORTA_MCP_PADRAO}/mcp"
    assert token == ""

    # 2. Com mcp_sessao.json gravado -> usa porta e token da sessão
    gravar_sessao_mcp(porta=27380, token="tok_secreto", diretorio_base=tmp_path)
    url2, token2 = descobrir_url_mcp_ativa(diretorio_base=tmp_path, env={})
    assert url2 == "http://127.0.0.1:27380/mcp"
    assert token2 == "tok_secreto"

    # 3. Com ARESTA_MCP_PORTA definido -> sobrepõe a porta
    url3, token3 = descobrir_url_mcp_ativa(
        diretorio_base=tmp_path, env={"ARESTA_MCP_PORTA": "29999"}
    )
    assert url3 == "http://127.0.0.1:29999/mcp"
    assert token3 == "tok_secreto"
