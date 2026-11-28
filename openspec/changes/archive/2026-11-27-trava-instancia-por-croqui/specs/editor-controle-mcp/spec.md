# Spec Delta

## MODIFIED Requirements

### Requirement: Suporte a Múltiplas Janelas por Croqui e Roteamento Proxy MCP
O Editor Aresta MUST substituir a trava global de instância única por uma trava escopada por croqui (`ArestaEditorCroqui_<id_croqui>`), permitindo múltiplas janelas abertas simultaneamente em croquis distintos. Cada instância MUST registrar sua porta e `id_croqui` em `mcp_sessoes.json`, preservando atomicamente a sessão primária ativa em `mcp_sessao.json` enquanto o processo primário permanecer ativo. O servidor MCP na porta principal `27378` MUST aceitar o parâmetro opcional `id_croqui` em todas as ferramentas de croqui e encaminhar transparentemente via proxy local as chamadas destinadas a outras janelas abertas.

#### Scenario: Abertura de um segundo croqui enquanto outro já está aberto
- **WHEN** a Janela #1 já está aberta com o croqui `"A"` e o cliente MCP chama `aresta_abrir_croqui_existente`, `aresta_importar_croqui_oficial` ou `aresta_criar_novo_croqui` para um croqui `"B"` diferente de `"A"`
- **THEN** a Janela #1 permanece aberta com `"A"`, uma nova janela independente é aberta para `"B"`, registrada em `mcp_sessoes.json`, e seus dados são retornados ao cliente

#### Scenario: Tentativa de abrir novamente um croqui que já está aberto
- **WHEN** o croqui `"A"` já está aberto em uma janela ativa e o cliente MCP ou o usuário solicita abrir `"A"` novamente
- **THEN** o sistema não cria uma segunda janela duplicada, ativa a janela existente de `"A"` e retorna os dados da sessão já aberta

#### Scenario: Roteamento proxy transparente por id_croqui na porta 27378
- **WHEN** há múltiplas janelas abertas (`"A"` na porta `27378` e `"B"` na porta `27379`) e o cliente MCP envia uma chamada na porta `27378` informando `id_croqui="B"`
- **THEN** o servidor na porta `27378` encaminha a requisição JSON-RPC para a porta `27379` e retorna a resposta ao cliente; se `id_croqui` for omitido havendo mais de um croqui aberto, retorna erro listando os `id_croqui` abertos

#### Scenario: Preservação da sessão primária em mcp_sessao.json com múltiplos processos ativos
- **WHEN** um segundo processo do editor inicia seu servidor MCP em uma porta secundária (`27379+`) enquanto o processo primário (`27378`) continua registrado e ativo em `mcp_sessoes.json`
- **THEN** o arquivo `mcp_sessoes.json` passa a listar ambas as sessões de forma atômica sob lock e `mcp_sessao.json` continua apontando para a sessão primária ativa até que ela seja encerrada
