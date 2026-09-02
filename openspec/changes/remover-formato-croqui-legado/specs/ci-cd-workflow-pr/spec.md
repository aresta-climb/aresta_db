## MODIFIED Requirements

### Requirement: Bot Validator on Pull Requests
O sistema MUST validar automaticamente Pull Requests que modifiquem o diretório `database/`.

#### Scenario: Pull Request validation succeeds
- **WHEN** um PR for aberto ou um novo commit for adicionado
- **THEN** o workflow MUST executar a validação de cabeçalhos/licenças e compilar as pastas modificadas via deploy de verificação
- **AND** postar um comentário no PR atestando o sucesso da validação sem geração nem upload de arquivos binários

#### Scenario: Pull Request validation fails
- **WHEN** um PR introduzir alterações que violem licenças ou quebrem a compilação
- **THEN** o workflow MUST falhar a execução (exit code != 0) para bloquear o merge
- **AND** postar um comentário contendo os erros de validação ou compilação
