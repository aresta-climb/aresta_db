# publicacao-croqui Specification

## Purpose
TBD - created by archiving change fix-croqui-duplication-on-rename. Update Purpose after archive.
## Requirements
### Requirement: Exclusão de Diretório Ancestral no Pull Request
O worker de publicação MUST remover o diretório referente ao ID ancestral do repositório oficial clonado, para evitar acumulação de histórico órfão caso o croqui tenha sido renomeado localmente.

#### Scenario: Publicação após Renomeação
- **WHEN** o processo de publicação inspeciona o `croqui_experimental.yaml` e nota que o `id_original` difere do ID atual
- **THEN** o worker comanda um `rmtree` na pasta ancestral antiga e um `git rm` do índice daquele diretório, preservando unicamente o id recém atualizado no Pull Request final

