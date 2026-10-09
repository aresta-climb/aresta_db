# Spec Delta

## MODIFIED Requirements

### Requirement: Bot Integrator on Pull Request Approval
O sistema MUST validar todas as checagens ativas do Pull Request antes de compilar o deploy, incluir as alterações de `generated/` e `database/` no commit automático, e realizar o merge automagicamente após aprovação humana somente se todas as validações forem bem-sucedidas.

#### Scenario: Automatic deploy and merge
- **WHEN** um revisor humano aprovar (`Approve`) o Pull Request
- **THEN** o workflow MUST aguardar até que todas as checagens ativas do PR concluam com sucesso
- **AND** executar o script `deploy_generated.py` para as pastas alteradas caso haja modificações em `database/`
- **AND** criar um commit no PR incluindo as pastas `generated/` e `database/` (com mensagem contendo `[skip ci]`)
- **AND** verificar se o status check do DCO pós-commit foi concluído e aprovado com sucesso antes de realizar o merge
- **AND** executar o merge automático do PR para a branch `main` se a checagem for bem-sucedida

#### Scenario: Merge blocked on failing or pending DCO
- **WHEN** o revisor humano aprovar o Pull Request mas o status check do DCO falhar ou não concluir com sucesso
- **THEN** o workflow MUST falhar com código de erro diferente de zero e bloquear o merge do Pull Request

#### Scenario: Execution blocked on failing or pending PR checks
- **WHEN** o revisor humano aprovar o Pull Request mas qualquer checagem ativa do PR falhar, for cancelada ou não concluir com sucesso
- **THEN** o workflow MUST abortar imediatamente com código de erro diferente de zero (fail-fast), sem gerar deploy nem realizar o merge do Pull Request

#### Scenario: Bot Bypass of Branch Protections
- **WHEN** o bot integrador tentar fazer push ou merge na branch `main`
- **THEN** ele MUST usar um GitHub App Token autenticado para ignorar regras de proteção (branch protection bypass)
