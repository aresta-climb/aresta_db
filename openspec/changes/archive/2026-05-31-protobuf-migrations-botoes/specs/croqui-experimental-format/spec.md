## MODIFIED Requirements

### Requirement: Database Directory Structure
The experimental croqui MUST contain a `database/` subdirectory matching the structure of a decompiled croqui. This directory MUST contain a `croqui.yaml` file, imported Markdown (`*.md`) parts, and an `imagens/` directory. O arquivo `croqui.yaml` conterá também o campo `ultima_migracao` e a nova lista de `botoes`.

#### Scenario: Decompiled data representation
- **WHEN** the user edits the croqui
- **THEN** the system updates the `croqui.yaml` and corresponding `*.md` files within the `database/` subdirectory
