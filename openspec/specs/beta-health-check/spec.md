# beta-health-check Specification

## Purpose
Define a detecção de betas pendentes de curadoria no relatório de saúde dos croquis (`STATUS_CROQUIS.md`) e a emissão de avisos e limpeza de `curadoria_betas` durante a compilação final.

## Requirements

### Requirement: Medição de Betas Pendentes na Saúde dos Croquis
O sistema SHALL detectar betas pendentes de curadoria (`betas_nao_scorados` e `betas_nao_revisados` em `curadoria_betas.md`), emitir aviso (Warning) durante a compilação do croqui (`preparar_submissao_lib.py`), reportar o estado na tabela `STATUS_CROQUIS.md` (`medir_saude_croquis.py`) e garantir que `curadoria_betas` seja removido antes de serializar `compilado.binarypb` e `compilado.yaml`.

#### Scenario: Detecção de betas pendentes
- **WHEN** o script `scripts/medir_saude_croquis.py` analisa a pasta de um croqui
- **THEN** ele MUST verificar as listas `betas_nao_scorados` e `betas_nao_revisados` em `curadoria_betas.md` (referenciado por `croqui.yaml`).
- **THEN** caso a soma de itens em `betas_nao_scorados` e `betas_nao_revisados` seja maior que zero, a coluna de betas pendentes no relatório Markdown MUST exibir `⚠️ (<contagem>)`; caso exista apenas `betas_rejeitados` ou nenhum item pendente, MUST exibir `✅`.

#### Scenario: Emissão de warning na compilação e exclusão de curadoria_betas do binário final
- **WHEN** o compilador (`preparar_submissao_lib.py`) compila um croqui que possui itens em `betas_nao_scorados` ou `betas_nao_revisados` dentro de `curadoria_betas`
- **THEN** o compilador MUST emitir uma mensagem de `AVISO` listando a quantidade de betas pendentes de revisão para incentivar a curadoria.
- **THEN** o compilador MUST limpar o campo `curadoria_betas` (`ClearField("curadoria_betas")`) antes de gravar `compilado.binarypb` e `compilado.yaml`, garantindo que apenas `Escalada.betas` (aprovados) esteja presente no pacote publicado.
