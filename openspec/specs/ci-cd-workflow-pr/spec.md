## Purpose
Define os workflows de automação e validação contínua (CI/CD) para Pull Requests no repositório.

## Requirements

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

### Requirement: Bot Integrator on Pull Request Approval
O sistema MUST gerar arquivos de deploy para produção e realizar o merge automagicamente após aprovação humana.

#### Scenario: Automatic deploy and merge
- **WHEN** um revisor humano aprovar (`Approve`) o Pull Request
- **THEN** o workflow MUST executar o script `deploy_generated.py` para as pastas alteradas
- **AND** criar um commit no PR contendo os arquivos gerados (com mensagem contendo `[skip ci]`)
- **AND** executar o merge automático do PR para a branch `main`

#### Scenario: Bot Bypass of Branch Protections
- **WHEN** o bot integrador tentar fazer push ou merge na branch `main`
- **THEN** ele MUST usar um GitHub App Token autenticado para ignorar regras de proteção (branch protection bypass)
