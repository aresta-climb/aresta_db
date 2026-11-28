# Spec Delta

## MODIFIED Requirements

### Requirement: Avaliação de Betas por Sub-agentes Antigravity
O sistema SHALL delegar a avaliação semântica de `betas_nao_scorados` a sub-agentes `AvaliadorBetas` (ou alternativa equivalente em clientes MCP sem subagentes nativos), calibrando `llm_confidence_score` (`>= 80`), propagando `id_croqui` ao servidor `editor-aresta` e proibindo remoção autônoma de betas durante a avaliação.

#### Scenario: Avaliação de lote de candidatos por sub-agente
- **WHEN** um sub-agente `AvaliadorBetas` é invocado com um lote de escaladas contendo itens em `betas_nao_scorados`
- **THEN** ele MUST analisar os metadados geográficos (nome da via, grau, setor, grupo, pico, cidade e estado), o título, a URL e os `snippets` coletados de cada candidato.
- **THEN** ele MUST atribuir um score de confiança (`llm_confidence_score` de 0 a 100) e uma justificativa textual (`llm_reasoning`) sabendo que notas **`>= 80`** são elegíveis para **aprovação automática em lote** pelo curador no Editor:
  - **`80 a 100`**: reservado exclusivamente para vídeos, reels, posts ou relatos em primeira mão que inequivocamente mostram ou detalham a escalada daquela via específica naquele pico.
  - **`50 a 79`**: menções parciais ou ambíguas que exigem verificação manual humana.
  - **`0 a 49` (e `< 30` para agregadores/PDFs)**: páginas que apenas referenciam PDFs ou guias antigos (como Scribd), agregadores de croquis, vias homônimas em outros locais ou conteúdos sem beta real.
- **THEN** os candidatos avaliados MUST ser movidos de `betas_nao_scorados` para `betas_nao_revisados` no modelo do croqui via MCP (`aresta_pontuar_betas`), ordenados por score decrescente, sem invocar `aresta_remover_betas` de forma autônoma.

### Requirement: Orquestração no Workflow Antigravity
O sistema SHALL disponibilizar as skills `coletar_betas_croqui`, `avaliar_betas_croqui` e `resolver_feedback_croqui` operando com o servidor MCP `editor-aresta` e propagando `id_croqui` em múltiplas janelas, cobrindo coleta, listagem paginada, pontuação, enfileiramento manual para revisão e remoção explícita.

#### Scenario: Coleta autônoma de betas via MCP em croqui de qualquer porte
- **WHEN** o usuário solicita ao agente conectado via MCP a coleta de betas do croqui (ou de um setor específico) usando a skill `coletar_betas_croqui`
- **THEN** o agente MUST identificar e propagar `id_croqui` quando houver múltiplos croquis abertos, invocar `aresta_coletar_betas(acao="iniciar")` e acompanhar o progresso via `aresta_coletar_betas(acao="status")` (ou agendamento de timer) até que `status` seja `"concluido"`, sem bloquear a UI do Editor Aresta e preservando o progresso incremental em micro-lotes

#### Scenario: Execução orquestrada da avaliação paginada de betas não scorados
- **WHEN** o usuário solicita ao agente conectado via MCP a avaliação dos betas não scorados usando a skill `avaliar_betas_croqui`
- **THEN** o agente MUST propagar `id_croqui` em todas as chamadas ao servidor `editor-aresta`, consultar as escaladas pendentes de forma paginada com `aresta_listar_betas_nao_scorados`, avaliar em lotes paralelos (via `AvaliadorBetas` no Antigravity ou alternativa equivalente no cliente MCP ativo) e persistir os itens pontuados em `betas_nao_revisados` via `aresta_pontuar_betas`

#### Scenario: Adição e remoção explícita de betas na curadoria via skills MCP
- **WHEN** o usuário ou mantenedor solicita explicitamente adicionar um link de beta para revisão ou remover um beta específico de uma escalada
- **THEN** o agente MUST utilizar `aresta_adicionar_betas_revisao` para enfileirar o link para revisão humana ou `aresta_remover_betas` para removê-lo da escalada/fila (registrando em `betas_rejeitados` por padrão contra re-scraping)
