# Tasks

## 1. Saneamento de Sessões Órfãs e Promoção Atômica de Porta (`sessao.py` e `bridge.py`)

- [x] 1.1 (TDD) Implementar em `editor/mcp/sessao.py` (com testes de comportamento em `editor/mcp/sessao_test.py`) a resolução da porta alvo primária, `vincular_porta_especifica_mcp`, `promover_sessao_porta_mcp` e `listar_sessoes_mcp_ativas` (podando entradas órfãs cujos sockets não estão mais vinculados e promovendo `mcp_sessao.json` em `obter_porta_primaria_ativa`), validando com `uv run pytest editor/mcp/sessao_test.py --cov=editor.mcp.sessao --cov-report=term-missing`.
- [x] 1.2 (TDD) Implementar failover automático em `editor/mcp/bridge.py` (com testes reais em `editor/mcp/bridge_test.py`) para que, quando a porta de `mcp_sessao.json` recusar conexão após morte abrupta da 1ª janela, a ponte `stdio` pode a sessão morta, promova e encaminhe a requisição para a sessão sobrevivente em `mcp_sessoes.json`, validando com `uv run pytest editor/mcp/bridge_test.py --cov=editor.mcp.bridge --cov-report=term-missing`.

## 2. Reaquisição Automática da Porta Primária e Proxy Resiliente (`servidor.py` e `ferramentas_ciclo_vida.py`)

- [x] 2.1 (TDD) Implementar em `editor/mcp/servidor.py` e `editor/mcp/ferramentas_ciclo_vida.py` (com testes de integração reais em `editor/mcp/servidor_test.py` e `editor/mcp/ferramentas_ciclo_vida_test.py`) a vigia daemon leve para reaquisição automática da porta primária `27378` por servidores secundários (mantendo a porta secundária ativa como alias), o uso de `listar_sessoes_mcp_ativas` no roteamento e em `aresta_listar_croquis`, e a blindagem de `_encaminhar_via_proxy` sem `processEvents()` fora da main thread e com tratamento de `httpx.HTTPError`, validando 100% de cobertura com `uv run pytest editor/mcp/servidor_test.py editor/mcp/ferramentas_ciclo_vida_test.py --cov=editor.mcp.servidor --cov=editor.mcp.ferramentas_ciclo_vida --cov-report=term-missing`.

## 3. Ciclo de Vida Multi-Janela no Mesmo Processo (`main.py` e `area_principal.py`)

- [x] 3.1 (TDD) Implementar no `ControladorAplicativo` (`editor/main.py`) e em `JanelaPrincipal` (`editor/legacy_views/area_principal.py`), com testes de integração reais em `editor/main_test.py`, o rastreamento de fechamento de `janela_principal` e `janelas_secundarias`, promovendo automaticamente uma janela secundária sobrevivente quando a primeira janela é fechada pelo usuário e mantendo o servidor MCP operante na porta primária, validando com `uv run pytest editor/main_test.py`.

## 4. Verificação Integrada de Arquitetura e Cobertura

- [x] 4.1 Executar a suíte completa de testes de MCP, arquitetura MVC e ciclo de vida do editor (`uv run pytest editor/mcp/ editor/arquitetura_mvc_test.py editor/views/dialogos/dialogo_conexao_mcp_test.py editor/main_test.py --cov=editor.mcp --cov-report=term-missing`) garantindo 100% de cobertura comportamental em `editor/mcp` e zero regressões.

## Workflow follow-up

- Sincronizar o delta spec em `openspec/specs/editor-controle-mcp/spec.md`, validar com `openspec validate --specs` e arquivar a mudança `failover-mcp-multi-janela`.
- Realizar commit assinado (`-s`) apenas dos arquivos da mudança e enviar (`git push`).
