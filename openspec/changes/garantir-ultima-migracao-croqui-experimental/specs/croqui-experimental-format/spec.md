# Spec Delta

## MODIFIED Requirements

### Requirement: Database Directory Structure
The experimental croqui MUST contain a `database/` subdirectory matching the structure of a decompiled croqui. This directory MUST contain a `croqui.yaml` file, imported Markdown (`*.md`) parts, and an `imagens/` directory. O arquivo `croqui.yaml` conterá também a lista de `botoes` e o campo `ultima_migracao`, que MUST ser obrigatoriamente preenchido com a versão mais recente de migração do catálogo tanto na criação quanto em qualquer salvamento ou submissão.

#### Scenario: Decompiled data representation
- **WHEN** the user edits the croqui
- **THEN** the system updates the `croqui.yaml` and corresponding `*.md` files within the `database/` subdirectory

#### Scenario: Sincronização da última migração ao salvar ou submeter
- **WHEN** um croqui experimental for criado, salvo ou preparado para submissão
- **THEN** o sistema MUST assegurar que o campo `ultima_migracao` em `croqui.yaml` seja atualizado com o valor numérico da versão mais recente de migração disponível no repositório, nunca permanecendo zerado ou ausente
