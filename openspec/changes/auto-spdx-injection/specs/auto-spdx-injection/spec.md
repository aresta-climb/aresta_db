## ADDED Requirements

### Requirement: Injeção idempotente de SPDX no frontmatter Markdown
O sistema DEVE, durante a fase de `corrigir_database`, inspecionar arquivos Markdown da base de dados. Se o arquivo possuir frontmatter YAML e não possuir o campo `spdx-id`, a chave `spdx-id: ODbL-1.0` DEVE ser adicionada sem corromper o YAML original. Se não possuir frontmatter, o arquivo DEVE ser ignorado.

#### Scenario: Arquivo MD sem spdx-id
- **WHEN** o arquivo Markdown tem frontmatter válido mas falta `spdx-id`
- **THEN** o script adiciona `spdx-id: ODbL-1.0` e o arquivo é reescrito

#### Scenario: Arquivo MD já possui spdx-id
- **WHEN** o arquivo Markdown tem frontmatter e já possui `spdx-id: ODbL-1.0`
- **THEN** o arquivo permanece inalterado e não sofre writes desnecessários

#### Scenario: Arquivo MD sem frontmatter
- **WHEN** o arquivo Markdown não tem bloco YAML
- **THEN** o arquivo é ignorado

### Requirement: Injeção idempotente de SPDX no croqui.yaml
O sistema DEVE inspecionar os arquivos `.yaml` (`croqui.yaml`) da base. Se o campo `spdx-id` estiver ausente, ele DEVE ser adicionado.

#### Scenario: YAML sem spdx-id
- **WHEN** o arquivo `croqui.yaml` não possui `spdx-id`
- **THEN** a chave `spdx-id: ODbL-1.0` é adicionada ao dicionário YAML e o arquivo reescrito

#### Scenario: YAML já possui spdx-id
- **WHEN** o arquivo `croqui.yaml` já possui `spdx-id`
- **THEN** o arquivo não é salvo novamente por este motivo
