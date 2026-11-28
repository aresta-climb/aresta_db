# Proposal

## Why

O prompt copiado na aba **Betas** (`PainelCuradoria`) atualmente é uma string genérica que não informa o servidor MCP (`editor-aresta`), o `id_croqui` ativo nem como carregar a skill caso o agente esteja fora do repositório — fazendo a avaliação falhar logo na largada quando há múltiplas janelas abertas. Além disso, abrir o diálogo de conexão MCP em uma janela secundária expõe a porta secundária em vez da porta primária (`mcp_sessao.json`) que realiza o roteamento proxy, e ainda não existem ferramentas MCP canônicas para enfileirar um beta específico para revisão ou remover um beta por URL com bloqueio contra re-scraping.

## What Changes

- **Prompt e banner MCP contextuais na aba Betas (`PainelCuradoria`)**: gerar dinamicamente o texto do banner e o comando copiado para a área de transferência a partir do croqui ativo (`croqui.id` e `croqui.nome`), citando explicitamente o servidor MCP `editor-aresta`, o carregamento via `aresta_ler_skill(nome_skill="avaliar_betas_croqui")` quando fora do workspace local e a passagem obrigatória de `id_croqui` em todas as chamadas para avaliar todos os `betas_nao_scorados` do croqui (independentemente do filtro visual de escalada).
- **Resolução da porta primária no `DialogoConexaoMcp`**: introduzir `obter_porta_primaria_ativa` em `editor/mcp/sessao.py` para que `DialogoConexaoMcp`, `JanelaPrincipal._exibir_conexao_mcp` e `TelaDeCarregamento.ao_clicar_conectar_mcp` exibam sempre a porta da sessão primária registrada em `mcp_sessao.json` (`27378`), usando a porta local apenas como fallback quando não houver sessão primária ativa.
- **Novas ferramentas MCP de curadoria por URL (`aresta_adicionar_betas_revisao` e `aresta_remover_betas`)**:
  - `CroquiController.adicionar_betas_para_revisao` e `aresta_adicionar_betas_revisao`: inserem ou atualizam candidatos por `(escalada_uid, url)` com normalização de URL, inferência de `FonteMidia` via `classificar_fonte_url`, resgate incondicional de `betas_rejeitados` de volta para revisão (limpando eventual prefixo `[Query: ... | Auto-filtrado: ...]`), preservação de itens já aprovados em `Escalada.betas` e roteamento automático para `betas_nao_revisados` (ordenado por score quando `llm_confidence_score` e `llm_reasoning` forem informados) ou `betas_nao_scorados`.
  - `CroquiController.remover_betas_por_url` e `aresta_remover_betas`: removem mídias por `(escalada_uid, url)` de `Escalada.betas`, `betas_nao_revisados` ou `betas_nao_scorados`, movendo para `betas_rejeitados` quando `bloquear_futura_coleta=True` (padrão) ou removendo definitivamente (inclusive de `betas_rejeitados`) quando `bloquear_futura_coleta=False`, tudo em um único `CmdMacro` reversível no `QUndoStack`.
- **Atualização das skills de domínio (`avaliar_betas_croqui`, `coletar_betas_croqui`, `resolver_feedback_croqui`)**: documentar o servidor `editor-aresta`, a propagação de `id_croqui` em todas as chamadas MCP, a alternativa para clientes sem `define_subagent` (Cursor, Claude Desktop, Codex) e as regras de uso de `aresta_adicionar_betas_revisao` e `aresta_remover_betas` (restrita a solicitações explícitas do usuário/mantenedor).

## Capabilities

### New Capabilities

_(Nenhuma nova capacidade isolada; todas as evoluções ampliam capacidades já existentes no projeto.)_

### Modified Capabilities

- `curation-panel`: geração dinâmica do banner e do prompt MCP em `1. Betas Não Scorados` citando `editor-aresta`, `aresta_ler_skill` e `id_croqui` para avaliar todo o croqui.
- `editor-controle-mcp`: exibição da porta da sessão primária ativa (`mcp_sessao.json`) no `DialogoConexaoMcp` em cenários multi-janela e adição das ferramentas `aresta_adicionar_betas_revisao` e `aresta_remover_betas` com suporte completo a `Undo/Redo`.
- `avaliador-betas-subagente`: atualização das skills de coleta/avaliação de betas para propagar `id_croqui`, suportar clientes MCP sem subagentes nativos e governar `aresta_adicionar_betas_revisao` / `aresta_remover_betas`.

## Impact

- `coleta_de_betas/curadoria/painel_curadoria.py` e `coleta_de_betas/curadoria/painel_curadoria_test.py`
- `editor/mcp/sessao.py` e `editor/mcp/sessao_test.py`
- `editor/views/dialogos/dialogo_conexao_mcp.py` e `editor/views/dialogos/dialogo_conexao_mcp_test.py`
- `editor/legacy_views/area_principal.py`, `editor/legacy_views/area_principal_test.py`, `editor/legacy_views/tela_de_carregamento.py` e `editor/legacy_views/tela_de_carregamento_test.py`
- `editor/controllers/croqui_controller.py` e `editor/controllers/croqui_controller_test.py`
- `editor/mcp/ferramentas_betas.py`, `editor/mcp/ferramentas_betas_test.py` e `editor/mcp/registro_ferramentas_test.py`
- `.agents/skills/avaliar_betas_croqui/SKILL.md`, `.agents/skills/coletar_betas_croqui/SKILL.md` e `.agents/skills/resolver_feedback_croqui/SKILL.md`
