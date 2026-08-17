# beta-intelligence Specification

## Purpose
TBD - created by archiving change coleta-de-betas. Update Purpose after archive.
## Requirements
### Requirement: Avaliação LLM de Candidatos
O sistema SHALL avaliar a relevância dos candidatos brutos gerados pela etapa de busca e extrair a inteligência contida nos snippets de texto usando sub-agentes Antigravity.

#### Scenario: Extração de inteligência do Beta e Metadados
- **WHEN** o sub-agente recebe a descrição (snippet) e o título da mídia candidata, incluindo flags de múltiplas fontes (ex: retornado pelo Google e DDG)
- **THEN** ele MUST atribuir um score de confiança (0-100) valorizando mídias que tenham confirmação cruzada (match de nome nos snippets do Google e DDG para a mesma URL).
- **THEN** ele MUST gerar uma string de justificativa (`llm_reasoning`) para popular a estrutura `ResultadoLLMBeta`.

