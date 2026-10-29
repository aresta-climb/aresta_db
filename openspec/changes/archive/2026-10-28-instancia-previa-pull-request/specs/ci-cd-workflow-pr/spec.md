# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Limpeza de Artefatos ao Encerrar Pull Request
O sistema MUST remover automaticamente todos os objetos publicados sob o prefixo `pr/<numero_pr>/` no bucket Cloudflare R2 quando a Pull Request for fechada ou mergeada.

#### Scenario: Pull Request é fechada ou mergeada
- **WHEN** o evento `pull_request` com tipo `closed` for disparado para uma Pull Request
- **THEN** o workflow remove em lote todos os objetos existentes sob a chave `pr/<numero_pr>/` no bucket R2 `aresta-serving`
