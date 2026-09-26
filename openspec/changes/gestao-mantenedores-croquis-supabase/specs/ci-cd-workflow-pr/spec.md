## MODIFIED Requirements

### Requirement: Bot Integrator on Pull Request Approval
O sistema MUST gerar arquivos de deploy para produção e realizar o merge automagicamente após aprovação humana de colaboradores ou aprovação delegada emitida pelo GitHub App em nome de mantenedor local autorizado.

#### Scenario: Automatic deploy and merge
- **WHEN** um revisor humano (`OWNER`, `MEMBER`, `COLLABORATOR`) ou o GitHub App autorizado em nome de mantenedor local aprovar (`Approve` ou `/approve`) o Pull Request
- **THEN** o workflow MUST executar o script `deploy_generated.py` para as pastas alteradas
- **AND** criar um commit no PR contendo os arquivos gerados (com mensagem contendo `[skip ci]`)
- **AND** executar o merge automático do PR para a branch `main`

#### Scenario: Bot Bypass of Branch Protections
- **WHEN** o bot integrador tentar fazer push ou merge na branch `main`
- **THEN** ele MUST usar um GitHub App Token autenticado para ignorar regras de proteção (branch protection bypass)
