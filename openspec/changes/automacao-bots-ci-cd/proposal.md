## Why

A aprovação e publicação de croquis na base de dados (repositório) atualmente depende de deploy manual, sem um fluxo robusto que valide tecnicamente as modificações antes do merge. Com a crescente adesão aos Pull Requests automáticos no `aresta_db`, precisamos garantir que (1) nenhuma alteração quebre a compilação, (2) que os revisores humanos foquem na revisão do conteúdo e não no deploy técnico, e (3) que a branch `main` esteja sempre com os artefatos de deploy sincronizados automaticamente.

## What Changes

- **Validação de PR (Bot 1):** Sempre que houver um novo commit no PR, um script validará as pastas de `database/` modificadas, compilará o croqui, e gerará um artefato exportável `.croqui` (usando formato experimental zipado e ofuscado com XOR 0xFF). O resultado (sucesso e warnings, ou erro) será postado como comentário.
- **Prevenção de Erros:** O Bot 1 bloqueará o botão de Merge caso a compilação de alguma das pastas modicadas falhe.
- **Integração e Deploy (Bot 2):** Ao receber uma aprovação (`Approve`) de um revisor humano no PR, e tendo o Bot 1 dado sinal verde, este bot fará a compilação real dos dados de produção (rodando `deploy_generated.py`), fará um commit automático desses artefatos de volta na branch do PR usando um GitHub App Token, e fará o merge para a `main`.
- **Bypass de Proteções:** O uso de um GitHub App Token pelo Bot 2 garante que ele possua os privilégios necessários para forçar um commit e um merge mesmo contra regras de proteção ativas na `main`.
- **Refatoração Headless:** Separação da lógica de geração de "croqui experimental" (atualmente no Editor, `croqui_experimental.py`) em scripts Python independentes e testáveis fora da interface gráfica (TDD na pasta `serving`).

## Capabilities

### New Capabilities
- `ci-cd-workflow-pr`: Define o fluxo de eventos e respostas dos GitHub Actions para validação, integração e push autônomo na branch principal.
- `empacotamento-headless`: Extensão da lógica de empacotamento e compilação do editor (formato `.croqui`) para suportar invocação sem interface gráfica via CLI.

### Modified Capabilities

- Nenhuma capability existente será alterada.

## Impact

- **Código:** Criação e refatoração na pasta `scripts/` e `serving/`. `deploy_generated.py` será alterado para aceitar múltiplos `--target`. O código seguirá os mandamentos do `PRINCIPIOS.md`, com 100% de cobertura de testes unitários (TDD obrigatório), docstrings claras e tudo 100% em português brasileiro.
- **Repositório:** Adoção pesada do diretório `.github/workflows/`.
- **Sistemas:** O repositório passa a necessitar da configuração de um GitHub App integrado, além de regras de proteção de branch mais estritas na `main`.
