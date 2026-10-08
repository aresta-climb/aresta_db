# Spec Delta

## MODIFIED Requirements

### Requirement: Bot Validator on Pull Requests
O sistema MUST validar automaticamente Pull Requests que modifiquem o diretório `database/`.

#### Scenario: Pull Request validation succeeds
- **WHEN** um PR for aberto ou um novo commit for adicionado
- **THEN** o workflow MUST executar a validação de cabeçalhos/licenças, conferir se a `ultima_migracao` dos croquis modificados corresponde à versão atual do repositório, e compilar as pastas modificadas via deploy de verificação
- **AND** postar um comentário no PR atestando o sucesso da validação sem geração nem upload de arquivos binários

#### Scenario: Pull Request validation fails
- **WHEN** um PR introduzir alterações que violem licenças, quebrem a compilação ou contenham `ultima_migracao` desatualizada ou zerada
- **THEN** o workflow MUST falhar a execução (exit code != 0) para bloquear o merge
- **AND** postar um comentário contendo os erros de validação ou compilação
