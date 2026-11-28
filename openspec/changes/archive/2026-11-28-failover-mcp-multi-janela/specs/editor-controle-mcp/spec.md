# Spec Delta

## ADDED Requirements

### Requirement: Failover Automático da Porta Primária e Saneamento de Sessões MCP Órfãs
Quando a janela detentora da porta MCP primária (`27378` ou `ARESTA_MCP_PORTA`) for encerrada limpa ou abruptamente, uma janela sobrevivente em porta secundária MUST adquirir automaticamente a porta primária em segundo plano, promovendo sua sessão em `mcp_sessao.json` e `mcp_sessoes.json` sem interromper sua porta secundária nem exigir reconfiguração do cliente. Sessões cujas portas locais não estejam mais ativas MUST ser podadas no roteamento, na listagem e na ponte `stdio`.

#### Scenario: Reaquisição automática da porta 27378 após fechamento ou morte abrupta da primeira janela
- **WHEN** a Janela #1 (na porta primária `27378` com o croqui `"A"`) é fechada ou encerrada abruptamente (`kill`) enquanto a Janela #2 (iniciada em porta secundária `27379+` com o croqui `"B"`) permanece aberta
- **THEN** a Janela #2 adquire automaticamente o listener HTTP/SSE na porta `27378` (mantendo também sua porta secundária ativa), remove o registro órfão de `"A"`, atualiza `mcp_sessao.json` e `mcp_sessoes.json` para apontar para `"B"` na porta `27378`, e responde às chamadas MCP enviadas a `127.0.0.1:27378` sem exigir `id_croqui` quando restar apenas `"B"` aberto

#### Scenario: Eleição entre múltiplas janelas sobreviventes e manutenção do proxy
- **WHEN** três janelas estão abertas (`"A"` em `27378`, `"B"` em `27379` e `"C"` em `27380`) e a Janela #1 (`"A"`) é encerrada
- **THEN** exatamente uma das janelas sobreviventes assume a porta `27378`, atualiza o registro de sessões ativas apenas com `"B"` e `"C"`, e passa a encaminhar via proxy local as chamadas na porta `27378` destinadas ao `id_croqui` da outra janela sobrevivente

#### Scenario: Poda automática de sessão secundária encerrada abruptamente
- **WHEN** uma janela secundária (`"B"` na porta `27379`) é encerrada abruptamente sem desregistrar sua sessão enquanto a Janela #1 (`"A"` na porta `27378`) continua aberta
- **THEN** o servidor MCP e a listagem `aresta_listar_croquis` descartam a sessão inativa da porta `27379`, removem-na de `mcp_sessoes.json` e voltam a operar sobre `"A"` sem exigir desambiguação por `id_croqui`

#### Scenario: Failover automático da ponte stdio quando mcp_sessao.json aponta para porta inativa
- **WHEN** um cliente conectado via ponte `stdio` envia uma requisição JSON-RPC enquanto `mcp_sessao.json` ainda referencia uma porta recém-encerrada, mas existe outra sessão ativa em `mcp_sessoes.json`
- **THEN** a ponte `stdio` descobre a sessão sobrevivente ativa, promove-a em `mcp_sessao.json`, poda a entrada morta e entrega a resposta JSON-RPC sem erro de conexão

#### Scenario: Fechamento da primeira janela quando múltiplas janelas coexistem no mesmo processo
- **WHEN** duas janelas estão abertas dentro do mesmo processo do aplicativo e o usuário fecha a primeira janela mantendo a segunda aberta
- **THEN** o aplicativo promove a janela sobrevivente sem encerrar o loop de eventos e mantém o servidor MCP respondendo normalmente na porta primária para o croqui da segunda janela
