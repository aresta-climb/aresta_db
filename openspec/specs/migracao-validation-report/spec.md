# migracao-validation-report Specification

## Purpose
Geração de relatório de validação da migração 0002 para facilitar a identificação e correção de IDs de mapa ausentes no banco de dados.

## Requirements

### Requirement: Relatório de Validação da Migração 0002
O sistema SHALL gerar um relatório estruturado informando quais IDs não foram encontrados ou tiveram um match parcial durante a validação da migração 0002.

#### Scenario: Geração de Relatório de IDs Ausentes
- **WHEN** a migração tenta processar referências de IDs que não existem de forma exata no frontmatter
- **THEN** o sistema adiciona o ID correspondente ao relatório `ids_no_mapa_nao_encontrados.yaml`

#### Scenario: Match Parcial de IDs
- **WHEN** o ID fornecido nas entidades (como escaladas) contém partes correspondentes, mas não é um match exato contra o parser estrito
- **THEN** o sistema também marca esses IDs para geração no arquivo `ids_no_mapa_nao_encontrados.yaml` permitindo que sejam ajustados manualmente no editor
