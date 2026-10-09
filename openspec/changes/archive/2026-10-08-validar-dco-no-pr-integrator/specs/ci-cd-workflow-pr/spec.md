# Spec Delta

## MODIFIED Requirements

### Requirement: Bot Integrator on Pull Request Approval
O sistema MUST gerar arquivos de deploy para produção e realizar o merge automagicamente após aprovação humana, verificando previamente a conformidade do DCO.

#### Scenario: Automatic deploy and merge
- **WHEN** um revisor humano aprovar (`Approve`) o Pull Request
- **THEN** o workflow MUST executar o script `deploy_generated.py` para as pastas alteradas
- **AND** criar um commit no PR contendo os arquivos gerados (com mensagem contendo `[skip ci]`)
- **AND** verificar se o status check do DCO foi concluído e aprovado com sucesso antes de realizar o merge
- **AND** executar o merge automático do PR para a branch `main` se a checagem for bem-sucedida

#### Scenario: Merge blocked on failing or pending DCO
- **WHEN** o revisor humano aprovar o Pull Request mas o status check do DCO falhar ou não concluir com sucesso
- **THEN** o workflow MUST falhar com código de erro diferente de zero e bloquear o merge do Pull Request

#### Scenario: Bot Bypass of Branch Protections
- **WHEN** o bot integrador tentar fazer push ou merge na branch `main`
- **THEN** ele MUST usar um GitHub App Token autenticado para ignorar regras de proteção (branch protection bypass)
