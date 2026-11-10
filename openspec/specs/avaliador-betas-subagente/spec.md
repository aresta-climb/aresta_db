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
O sistema SHALL disponibilizar uma skill dedicada (`.agents/skills/avaliar_betas_croqui/SKILL.md`) e atualizar o workflow `.agents/workflows/coletar_betas.md` para operar de forma integrada com o servidor MCP do Editor Aresta e com o campo `curadoria_betas` do `Croqui`.

#### Scenario: Execução orquestrada do workflow
- **WHEN** o usuário solicita ao agente conectado via MCP a avaliação dos betas não scorados (seguindo as instruções da aba **Betas** ou invocando `/coletar_betas`)
- **THEN** o agente MUST carregar a skill `avaliar_betas_croqui`, ler os `betas_nao_scorados` do croqui via MCP, particionar em lotes para sub-agentes `AvaliadorBetas` em paralelo e persistir os itens pontuados em `betas_nao_revisados`.
