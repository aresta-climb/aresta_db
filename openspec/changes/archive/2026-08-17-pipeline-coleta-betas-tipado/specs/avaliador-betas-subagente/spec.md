## ADDED Requirements

### Requirement: Avaliação de Betas por Sub-agentes Antigravity
O sistema SHALL delegar a avaliação de candidatos a betas a sub-agentes nativos do Antigravity (`AvaliadorBetas`), eliminando chamadas a SDKs ou APIs de IA externas.

#### Scenario: Avaliação de lote de candidatos por sub-agente
- **WHEN** um sub-agente `AvaliadorBetas` é invocado com um lote de vias e candidatos de `candidatos_brutos.yaml`
- **THEN** ele MUST analisar os metadados geográficos, nomes, snippets e URLs de thumbnail de cada candidato.
- **THEN** ele MUST atribuir um score de confiança (0-100) e uma justificativa textual (`llm_reasoning`).
- **THEN** ele MUST retornar a lista avaliada estruturada em formato YAML.

### Requirement: Orquestração no Workflow Antigravity
O sistema SHALL fornecer o workflow `.agents/workflows/coletar_betas.md` para orquestrar o pipeline completo: extração de vias, busca, disparo paralelo de sub-agentes e geração do staging.

#### Scenario: Execução orquestrada do workflow
- **WHEN** o usuário invoca `/coletar_betas database/<croqui>`
- **THEN** o orquestrador MUST executar a extração de vias, a busca tripla, o particionamento em batches para sub-agentes e o salvamento final do staging `betas_pendentes.binarypb`.
