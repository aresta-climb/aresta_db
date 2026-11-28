# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import socket
from pathlib import Path

from editor.core.storage import obter_diretorio_base_app
from editor.mcp.sessao import (
    NOME_ARQUIVO_SESSAO_MCP,
    PORTA_MCP_PADRAO,
    DadosSessaoMcp,
    alocar_porta_mcp,
    descobrir_url_mcp_ativa,
    desregistrar_sessao_multi_mcp,
    gravar_sessao_mcp,
    ler_sessao_mcp,
    listar_sessoes_mcp,
    obter_caminho_sessao_mcp,
    obter_caminho_sessoes_mcp,
    obter_porta_primaria_ativa,
    porta_disponivel_local,
    registrar_sessao_multi_mcp,
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


def test_registro_multi_sessao_mcp(tmp_path: Path):
    """Valida registro, atualização, listagem e remoção de múltiplas sessões em mcp_sessoes.json."""
    assert listar_sessoes_mcp(tmp_path) == []

    s1 = gravar_sessao_mcp(
        porta=27378,
        token="tok1",
        diretorio_base=tmp_path,
        id_croqui="croqui_a",
        caminho_database="/db/a",
    )
    s2 = gravar_sessao_mcp(
        porta=27379,
        token="tok2",
        diretorio_base=tmp_path,
        id_croqui="croqui_b",
        caminho_database="/db/b",
    )
    sessoes = listar_sessoes_mcp(tmp_path)
    assert len(sessoes) == 2
    assert [s.id_croqui for s in sessoes] == ["croqui_a", "croqui_b"]
    assert [s.porta for s in sessoes] == [27378, 27379]

    # Atualizar o id_croqui na mesma porta substitui o registro sem duplicar
    registrar_sessao_multi_mcp(
        DadosSessaoMcp(
            porta=27378,
            pid=s1.pid,
            token=s1.token,
            id_croqui="croqui_a_renomeado",
            caminho_database="/db/a2",
        ),
        diretorio_base=tmp_path,
    )
    sessoes_atualizadas = listar_sessoes_mcp(tmp_path)
    assert len(sessoes_atualizadas) == 2
    assert sessoes_atualizadas[0].id_croqui == "croqui_a_renomeado"

    # Remover a porta 27378 preserva a 27379 e promove-a em mcp_sessao.json
    remover_sessao_mcp(tmp_path, porta=27378)
    restantes = listar_sessoes_mcp(tmp_path)
    assert len(restantes) == 1
    assert restantes[0].porta == 27379
    sessao_principal = ler_sessao_mcp(tmp_path)
    assert sessao_principal is not None
    assert sessao_principal.porta == 27379

    # Desregistrar a última sessão limpa mcp_sessoes.json e mcp_sessao.json
    desregistrar_sessao_multi_mcp(27379, tmp_path)
    assert listar_sessoes_mcp(tmp_path) == []
    assert not obter_caminho_sessoes_mcp(tmp_path).exists()

    # Arquivo mcp_sessoes.json corrompido retorna lista vazia de forma resiliente
    obter_caminho_sessoes_mcp(tmp_path).write_text("{corrompido", encoding="utf-8")
    assert listar_sessoes_mcp(tmp_path) == []


def test_gravar_sessao_preserva_primaria_e_sincroniza_atualizacao(tmp_path: Path) -> None:
    """Garante que sessões secundárias não sobrescrevem mcp_sessao.json e que updates da primária propagam."""
    s_prim = gravar_sessao_mcp(
        porta=27378,
        token="tok_prim",
        diretorio_base=tmp_path,
        id_croqui="croqui_prim",
        caminho_database="/db/prim",
    )
    gravar_sessao_mcp(
        porta=27379,
        token="tok_sec",
        diretorio_base=tmp_path,
        id_croqui="croqui_sec",
        caminho_database="/db/sec",
    )

    principal_atual = ler_sessao_mcp(tmp_path)
    assert principal_atual is not None
    assert principal_atual.porta == 27378
    assert principal_atual.id_croqui == "croqui_prim"

    # Atualizar a sessão primária via registrar_sessao_multi_mcp sincroniza também mcp_sessao.json
    registrar_sessao_multi_mcp(
        DadosSessaoMcp(
            porta=27378,
            pid=s_prim.pid,
            token="tok_prim",
            id_croqui="croqui_prim_atualizado",
            caminho_database="/db/prim2",
        ),
        diretorio_base=tmp_path,
    )
    principal_apos_update = ler_sessao_mcp(tmp_path)
    assert principal_apos_update is not None
    assert principal_apos_update.porta == 27378
    assert principal_apos_update.id_croqui == "croqui_prim_atualizado"

    # Atualizar a sessão secundária mantém mcp_sessao.json na primária
    registrar_sessao_multi_mcp(
        DadosSessaoMcp(
            porta=27379,
            pid=s_prim.pid,
            token="tok_sec",
            id_croqui="croqui_sec_atualizado",
            caminho_database="/db/sec2",
        ),
        diretorio_base=tmp_path,
    )
    principal_preservada = ler_sessao_mcp(tmp_path)
    assert principal_preservada is not None
    assert principal_preservada.porta == 27378
    assert principal_preservada.id_croqui == "croqui_prim_atualizado"


def test_obter_porta_primaria_ativa_prioriza_sessao_principal_com_fallbacks(tmp_path: Path) -> None:
    """Garante que obter_porta_primaria_ativa prioriza mcp_sessao.json e usa fallbacks apenas se ausente."""
    # 1. Sem sessão e sem fallback -> porta padrão inativa
    assert obter_porta_primaria_ativa(diretorio_base=tmp_path) == (PORTA_MCP_PADRAO, False)

    # 2. Sem sessão mas com porta fallback local -> retorna fallback ativo
    assert obter_porta_primaria_ativa(porta_fallback=27399, diretorio_base=tmp_path) == (
        27399,
        True,
    )

    # 3. Com sessão primária ativa -> ignora porta fallback da janela secundária e retorna a primária
    gravar_sessao_mcp(porta=27381, token="tok_prim", diretorio_base=tmp_path, id_croqui="croqui_1")
    gravar_sessao_mcp(porta=27382, token="tok_sec", diretorio_base=tmp_path, id_croqui="croqui_2")
    assert obter_porta_primaria_ativa(porta_fallback=27382, diretorio_base=tmp_path) == (
        27381,
        True,
    )


def test_listar_sessoes_mcp_ativas_poda_portas_mortas_e_promove_sobrevivente(
    tmp_path: Path,
) -> None:
    """
    Quando a janela primária morre abruptamente (sem remover_sessao_mcp), listar_sessoes_mcp_ativas
    e obter_porta_primaria_ativa devem podar a porta morta e promover a janela sobrevivente real.
    """
    from editor.mcp.sessao import (
        listar_sessoes_mcp_ativas,
        obter_porta_alvo_primaria_mcp,
        promover_sessao_porta_mcp,
        vincular_porta_especifica_mcp,
    )

    assert obter_porta_alvo_primaria_mcp(porta_preferencial=28001) == 28001
    assert obter_porta_alvo_primaria_mcp(env={"ARESTA_MCP_PORTA": "28002"}) == 28002
    assert obter_porta_alvo_primaria_mcp(env={}) == PORTA_MCP_PADRAO

    # Sem sessões -> lista vazia
    assert listar_sessoes_mcp_ativas(tmp_path) == []

    # Abre dois sockets reais simulando Janela 1 (primária) e Janela 2 (secundária)
    sock_j1, porta_j1 = alocar_porta_com_socket()
    sock_j2, porta_j2 = alocar_porta_com_socket()
    try:
        # Enquanto sock_j1 segura porta_j1, vincular_porta_especifica_mcp deve retornar None
        assert vincular_porta_especifica_mcp(porta_j1) is None

        gravar_sessao_mcp(
            porta=porta_j1,
            token="tok_j1",
            diretorio_base=tmp_path,
            id_croqui="croqui_j1",
        )
        s_j2 = gravar_sessao_mcp(
            porta=porta_j2,
            token="tok_j2",
            diretorio_base=tmp_path,
            id_croqui="croqui_j2",
        )

        # Ambas vivas -> preserva as duas sem podar
        ativas_ambas = listar_sessoes_mcp_ativas(tmp_path, porta_local_ativa=porta_j2)
        assert [s.porta for s in ativas_ambas] == [porta_j1, porta_j2]

        # Simula kill abrupto da Janela 1 fechando apenas o socket (sem chamar remover_sessao_mcp!)
        sock_j1.close()

        # obter_porta_primaria_ativa deve detectar que porta_j1 morreu e promover porta_j2
        assert obter_porta_primaria_ativa(porta_fallback=porta_j2, diretorio_base=tmp_path) == (
            porta_j2,
            True,
        )
        sessao_principal = ler_sessao_mcp(tmp_path)
        assert sessao_principal is not None
        assert sessao_principal.porta == porta_j2
        assert [s.porta for s in listar_sessoes_mcp(tmp_path)] == [porta_j2]

        # Agora Janela 2 readquire a porta_j1 livre e promove seu registro para porta_j1
        sock_rebind = vincular_porta_especifica_mcp(porta_j1)
        assert sock_rebind is not None
        try:
            promovida = promover_sessao_porta_mcp(s_j2, porta_j1, diretorio_base=tmp_path)
            assert promovida.porta == porta_j1
            assert promovida.id_croqui == "croqui_j2"
            assert ler_sessao_mcp(tmp_path) == promovida
            assert [s.porta for s in listar_sessoes_mcp(tmp_path)] == [porta_j1]

            # Se o desregistro tardio da janela 1 rodar depois da promoção, o token diferente impede apagar a promovida
            remover_sessao_mcp(tmp_path, porta=porta_j1, token="tok_j1")
            assert ler_sessao_mcp(tmp_path) == promovida
            assert [s.porta for s in listar_sessoes_mcp(tmp_path)] == [porta_j1]
        finally:
            sock_rebind.close()
    finally:
        sock_j1.close()
        sock_j2.close()

    # Com ambos os sockets fechados (todas mortas), listar_sessoes_mcp_ativas limpa ambos os arquivos
    assert listar_sessoes_mcp_ativas(tmp_path) == []
    assert ler_sessao_mcp(tmp_path) is None
    assert not obter_caminho_sessoes_mcp(tmp_path).exists()


def alocar_porta_com_socket() -> tuple[socket.socket, int]:
    from editor.mcp.sessao import vincular_socket_mcp

    sock, porta = vincular_socket_mcp(porta_preferencial=38100)
    sock.listen(1)
    return sock, porta
