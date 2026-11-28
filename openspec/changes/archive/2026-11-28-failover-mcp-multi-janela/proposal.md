# Proposal

## Why

Quando o usuário abre uma primeira janela do Editor Aresta (que vincula a porta MCP primária `27378`) e em seguida abre uma segunda janela (em outro processo do sistema operacional ou via `abrir_croqui_via_mcp` no mesmo processo, vinculando uma porta secundária `27379+`), encerrar ou matar (`kill`) a primeira janela derruba o listener da porta `27378` e deixa sessões zumbis em `mcp_sessao.json` e `mcp_sessoes.json`. Como os clientes MCP baseados em HTTP (`Antigravity`, `Codex`, `Cursor`) apontam estaticamente para `http://127.0.0.1:27378/mcp` e o roteador/ponte `stdio` não limpa sessões mortas nem promove o socket `27378`, o agente perde completamente a conexão com a segunda janela ainda aberta.

## What Changes

- **Reaquisição automática da porta primária (`27378`) por janelas secundárias (`ServidorMCP`)**: instâncias do `ServidorMCP` iniciadas em portas secundárias (`27379+`) passam a monitorar de forma assíncrona em background (sem tocar na thread principal do Qt) a liberação da porta primária alvo (`27378` ou `ARESTA_MCP_PORTA`). Assim que a janela primária é fechada ou morta (`kill`), uma janela sobrevivente adquire atomicamente o socket `27378` (`SO_EXCLUSIVEADDRUSE`), inicia um listener Uvicorn adicional na `27378` (preservando sua porta secundária viva como alias) e promove seu registro em `mcp_sessao.json` e `mcp_sessoes.json`.
- **Saneamento ativo de sessões órfãs/zumbis (`editor/mcp/sessao.py`, `servidor.py`, `ferramentas_ciclo_vida.py`, `bridge.py`)**: verificar vivacidade real via conexão TCP loopback (`127.0.0.1:<porta>`) e podar atomicamente de `mcp_sessoes.json` e `mcp_sessao.json` entradas cujos servidores morreram abruptamente (`kill`/crash), garantindo que `listar_sessoes_mcp_ativas`, `obter_porta_primaria_ativa`, `aresta_listar_croquis`, o roteamento automático sem `id_croqui` quando resta apenas 1 janela viva e a ponte `stdio` (`bridge.py`) façam failover imediato sem falso erro de múltiplos croquis.
- **Blindagem do proxy HTTP MCP sem `processEvents()` (`ServidorMCP._encaminhar_via_proxy`)**: eliminar o uso de `QCoreApplication.processEvents()` em threads de background (Princípio IX do `AGENTS.md`) e capturar `httpx.HTTPError` ao rotear para sessões remotas recém-encerradas, removendo a sessão morta e retornando erro JSON-RPC estruturado em vez de `IndexError`.
- **Gestão do ciclo de vida multi-janela no mesmo processo (`ControladorAplicativo` e `JanelaPrincipal`)**: rastrear o fechamento individual de `janela_principal` e de `janelas_secundarias` no `ControladorAplicativo`, promovendo automaticamente uma janela secundária sobrevivente quando a janela principal for fechada pelo usuário e reconectando `solicitar_abrir_novo`, mantendo o servidor MCP e o aplicativo íntegros até o fechamento da última janela.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability isolada; evolução direta de editor-controle-mcp. -->

### Modified Capabilities
- `editor-controle-mcp`: adiciona requisitos e cenários de failover automático da porta primária `27378` por janelas secundárias, poda ativa de sessões MCP órfãs após encerramento abrupto (`kill`), failover na ponte `stdio` e promoção limpa de janelas secundárias no mesmo processo.

## Impact

- `editor/mcp/sessao.py` e `editor/mcp/sessao_test.py`
- `editor/mcp/servidor.py` e `editor/mcp/servidor_test.py`
- `editor/mcp/bridge.py` e `editor/mcp/bridge_test.py`
- `editor/mcp/ferramentas_ciclo_vida.py` e `editor/mcp/ferramentas_ciclo_vida_test.py`
- `editor/main.py` e `editor/main_test.py`
- `editor/legacy_views/area_principal.py`
- `openspec/specs/editor-controle-mcp/spec.md`
