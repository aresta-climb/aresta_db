## Purpose
Define os workflows de automação e validação contínua (CI/CD) para Pull Requests no repositório.

## Requirements

### Requirement: Bot Validator on Pull Requests
O sistema MUST validar automaticamente Pull Requests que modifiquem o diretório `database/`, publicar a prévia compilada e o resumo de diferenças quando a validação for bem-sucedida, e manter apenas um único comentário atualizado no final da timeline da Pull Request.

#### Scenario: Pull Request validation succeeds
- **WHEN** um PR for aberto ou um novo commit for adicionado em `database/` e a validação concluir sem erros
- **THEN** o workflow MUST executar a validação de cabeçalhos/licenças, conferir se a `ultima_migracao` dos croquis modificados corresponde à versão atual do repositório, compilar as pastas modificadas e publicar os artefatos compilados e o `resumo.html` em `s3://aresta-serving/pr/<numero_pr>/`
- **AND** remover qualquer comentário anterior do bot na mesma Pull Request identificado pelo marcador invisível `<!-- aresta-pr-validator -->`
- **AND** criar um novo comentário no final da Pull Request contendo o marcador `<!-- aresta-pr-validator -->`, o resumo enxuto de contadores do diff, o código de pareamento (`pr00-0042`), o link direto para abrir no aplicativo (`https://previa.arestaclimb.com/<codigo_pr>`) e o link para o relatório visual completo (`https://previa.arestaclimb.com/resumo/<codigo_pr>`)

#### Scenario: Pull Request validation fails
- **WHEN** um PR introduzir alterações que violem licenças, quebrem a compilação ou contenham `ultima_migracao` desatualizada ou zerada
- **THEN** o workflow MUST falhar a execução (exit code != 0) para bloquear o merge sem sobrescrever nem publicar artefatos inválidos no R2
- **AND** remover qualquer comentário anterior do bot identificado por `<!-- aresta-pr-validator -->` e criar um novo comentário no final da Pull Request contendo os erros de validação ou compilação

### Requirement: Limpeza de Artefatos ao Encerrar Pull Request
O sistema MUST remover automaticamente todos os objetos publicados sob o prefixo `pr/<numero_pr>/` no bucket Cloudflare R2 quando a Pull Request for fechada ou mergeada.

#### Scenario: Pull Request é fechada ou mergeada
- **WHEN** o evento `pull_request` com tipo `closed` for disparado para uma Pull Request
- **THEN** o workflow remove em lote todos os objetos existentes sob a chave `pr/<numero_pr>/` no bucket R2 `aresta-serving`

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

