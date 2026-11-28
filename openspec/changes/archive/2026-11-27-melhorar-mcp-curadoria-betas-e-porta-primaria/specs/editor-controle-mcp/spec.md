# Spec Delta

## MODIFIED Requirements

### Requirement: Diálogo de Conexão de Agentes na Interface
O Editor Aresta MUST exibir na interface gráfica uma opção para abrir o diálogo `Conectar Agente de IA (MCP)`, apresentando o status de execução do servidor local, o endereço ativo da sessão primária e botões para copiar a configuração pronta para os principais clientes MCP.

#### Scenario: Cópia de configuração de agente em um clique
- **WHEN** o usuário abre o diálogo `Conectar Agente de IA (MCP)` e aciona o botão de copiar configuração para Antigravity, Codex, Claude Desktop ou Cursor
- **THEN** o sistema copia para a área de transferência o bloco de configuração formatado com os caminhos e a porta correspondentes ao ambiente em execução

#### Scenario: Priorização da porta primária ativa em múltiplas janelas abertas
- **WHEN** existem múltiplas janelas do Editor Aresta abertas (`27378` como sessão primária em `mcp_sessao.json` e `27379` como janela secundária) e o usuário abre `Conectar Agente de IA (MCP)` a partir da janela secundária (ou da `TelaDeCarregamento`)
- **THEN** o diálogo MUST exibir e copiar a URL da porta da sessão primária ativa (`mcp_sessao.json`), recorrendo à porta local apenas quando não existir sessão primária registrada

## ADDED Requirements

### Requirement: Adição e Remoção de Betas por URL na Curadoria via MCP
O servidor MCP MUST disponibilizar `aresta_adicionar_betas_revisao` e `aresta_remover_betas`, operando por `(escalada_uid, url)` com normalização de URL e reversibilidade atômica via `QUndoStack`.

#### Scenario: Adição de beta para revisão sem nota e com nota (incluindo resgate de rejeitados)
- **WHEN** o cliente MCP chama `aresta_adicionar_betas_revisao` com itens contendo `escalada_uid`, `url` e opcionalmente `titulo`, `fonte`, `snippets`, `llm_confidence_score` e `llm_reasoning`
- **THEN** o sistema valida todos os itens previamente (*fail-fast*), normaliza a URL, infere `FonteMidia` quando omitida, resgata o item caso esteja em `betas_rejeitados` (limpando eventual prefixo `[Query: ... | Auto-filtrado: ...]`), mantém intacto se já aprovado em `Escalada.betas`, e insere/atualiza o item em `betas_nao_revisados` (ordenado por score decrescente quando informado score + justificativa) ou em `betas_nao_scorados` (quando sem nota) em um único `CmdMacro`

#### Scenario: Rejeição fail-fast ao informar parâmetros inválidos em aresta_adicionar_betas_revisao
- **WHEN** um item em `aresta_adicionar_betas_revisao` informa `escalada_uid` inexistente, URL inválida/não classificável, `fonte` inválida, apenas um entre `llm_confidence_score` e `llm_reasoning`, ou score fora de `0..100`
- **THEN** a chamada falha antes de empilhar qualquer comando no histórico e o `CroquiModel` permanece inalterado

#### Scenario: Remoção de beta por URL com bloqueio contra re-scraping ou exclusão definitiva
- **WHEN** o cliente MCP chama `aresta_remover_betas` informando `escalada_uid` e `url` (com `bloquear_futura_coleta=True` padrão ou `False`)
- **THEN** o sistema remove a mídia correspondente de `Escalada.betas`, `betas_nao_revisados` ou `betas_nao_scorados`, movendo-a para `betas_rejeitados` quando `bloquear_futura_coleta=True` ou excluindo-a também de `betas_rejeitados` quando `bloquear_futura_coleta=False`, em um único `CmdMacro` reversível por `undo()`/`redo()`

#### Scenario: Rejeição fail-fast ao tentar remover URL ausente em aresta_remover_betas
- **WHEN** `aresta_remover_betas` recebe `escalada_uid` inexistente ou `url` não encontrada nas listas aplicáveis da escalada
- **THEN** a chamada falha antes de alterar qualquer estado no `CroquiModel` e retorna `isError: True`
