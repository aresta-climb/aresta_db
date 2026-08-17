# beta-health-check Specification

## Purpose
TBD - created by archiving change coleta-de-betas. Update Purpose after archive.
## Requirements
### Requirement: Medição de Betas Pendentes na Saúde dos Croquis
O sistema SHALL detectar e reportar croquis com betas pendentes de curadoria na tabela de saúde `STATUS_CROQUIS.md`.

#### Scenario: Detecção de betas pendentes
- **WHEN** o script `scripts/medir_saude_croquis.py` analisa a pasta de um croqui
- **THEN** ele MUST verificar se existe um arquivo `betas_pendentes.binarypb` com itens pendentes não resolvidos.
- **THEN** caso existam betas pendentes, a coluna de betas pendentes no relatório Markdown MUST sinalizar um estado de alerta/não saudável (ex: ⚠️ ou ❌ com a contagem de pendências).
- **THEN** caso não existam betas pendentes ou o croqui esteja 100% curado, a coluna MUST exibir estado saudável (ex: ✅).

