# avaliador-betas-subagente Specification

## Purpose
Define a avaliação semântica e pontuação de candidatos a betas (`betas_nao_scorados`) por sub-agentes `AvaliadorBetas` orquestrados via skill e servidor MCP do Editor Aresta.

## Requirements

### Requirement: Avaliação de Betas por Sub-agentes Antigravity
O sistema SHALL delegar a avaliação semântica dos itens presentes em `betas_nao_scorados` a sub-agentes nativos do Antigravity (`AvaliadorBetas`), calibrando o `llm_confidence_score` (0 a 100) de acordo com o limiar de aprovação em lote (`>= 80`) e lendo/gravando diretamente no `Croqui` aberto no Editor via servidor MCP.

#### Scenario: Avaliação de lote de candidatos por sub-agente
- **WHEN** um sub-agente `AvaliadorBetas` é invocado com um lote de escaladas contendo itens em `betas_nao_scorados`
- **THEN** ele MUST analisar os metadados geográficos (nome da via, grau, setor, grupo, pico, cidade e estado), o título, a URL e os `snippets` coletados de cada candidato.
- **THEN** ele MUST atribuir um score de confiança (`llm_confidence_score` de 0 a 100) e uma justificativa textual (`llm_reasoning`) sabendo que notas **`>= 80`** são elegíveis para **aprovação automática em lote** pelo curador no Editor:
  - **`80 a 100`**: reservado exclusivamente para vídeos, reels, posts ou relatos em primeira mão que inequivocamente mostram ou detalham a escalada daquela via específica naquele pico.
  - **`50 a 79`**: menções parciais ou ambíguas que exigem verificação manual humana.
  - **`0 a 49` (e `< 30` para agregadores/PDFs)**: páginas que apenas referenciam PDFs ou guias antigos (como Scribd), agregadores de croquis, vias homônimas em outros locais ou conteúdos sem beta real.
- **THEN** os candidatos avaliados MUST ser movidos de `betas_nao_scorados` para `betas_nao_revisados` no modelo do croqui via MCP (`aresta_alterar_campo` / `aresta_alterar_em_lote`), ordenados por score decrescente.

### Requirement: Orquestração no Workflow Antigravity
O sistema SHALL disponibilizar duas skills complementares — `.agents/skills/coletar_betas_croqui/SKILL.md` (para coleta multi-fonte em background via `aresta_coletar_betas` suportando croquis de 1.000+ vias) e `.agents/skills/avaliar_betas_croqui/SKILL.md` (para leitura paginada via `aresta_listar_betas_nao_scorados` e pontuação paralela com sub-agentes `AvaliadorBetas`) — operando de forma integrada com o servidor MCP do Editor Aresta e com o campo `curadoria_betas` do `Croqui`.

#### Scenario: Coleta autônoma de betas via MCP em croqui de qualquer porte
- **WHEN** o usuário solicita ao agente conectado via MCP a coleta de betas do croqui (ou de um setor específico) usando a skill `coletar_betas_croqui`
- **THEN** o agente MUST invocar `aresta_coletar_betas(acao="iniciar")`, acompanhar o progresso via `aresta_coletar_betas(acao="status")` (ou agendamento de timer) até que `status` seja `"concluido"`, sem bloquear a UI do Editor Aresta e preservando o progresso incremental em micro-lotes

#### Scenario: Execução orquestrada da avaliação paginada de betas não scorados
- **WHEN** o usuário solicita ao agente conectado via MCP a avaliação dos betas não scorados usando a skill `avaliar_betas_croqui`
- **THEN** o agente MUST consultar as escaladas pendentes de forma paginada com `aresta_listar_betas_nao_scorados` (evitando carregar `betas_rejeitados` ou fazer consultas individuais por escalada), particionar em lotes para sub-agentes `AvaliadorBetas` em paralelo e persistir os itens pontuados em `betas_nao_revisados` via `aresta_alterar_em_lote`
