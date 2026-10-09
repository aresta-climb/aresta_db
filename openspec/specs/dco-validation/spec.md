# dco-validation Specification

## Purpose
Garante que todas as contribuições submetidas via Pull Request no repositório estejam em conformidade legal com o Developer Certificate of Origin (DCO).
## Requirements
### Requirement: Validação Automática de Pull Requests (DCO)
O repositório no GitHub MUST ter a validação de DCO habilitada para todos os Pull Requests através do aplicativo oficial do DCO (Probot) ou Action equivalente, permitindo isenção para membros da organização em commits verificados.

#### Scenario: PR sem assinatura
- **WHEN** um usuário externo envia um Pull Request com algum commit sem a tag `Signed-off-by`
- **THEN** a verificação de status (status check) falha e o PR é bloqueado para merge até que o autor faça um amend no commit e inclua a assinatura.

#### Scenario: PR com assinatura válida
- **WHEN** um usuário envia um Pull Request onde todos os commits possuem a tag `Signed-off-by` com nome e email compatíveis com o autor do commit
- **THEN** a verificação de status passa com sucesso e o PR é liberado para as próximas etapas (ex: code review).

#### Scenario: Commit verificado por membro da organização
- **WHEN** um membro da organização submete commits verificados criptograficamente ou realizados diretamente pela interface web do GitHub sem tag `Signed-off-by`
- **THEN** a verificação de status do DCO passa com sucesso através da configuração `require.members: false` em `.github/dco.yml`.

