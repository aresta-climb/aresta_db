## MODIFIED Requirements

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
