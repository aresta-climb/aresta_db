## Why

Atualmente, o lançamento do Editor Aresta no GitHub Actions exige que o operador digite manualmente a versão semântica exata (`new_version`). Essa abordagem manual introduz risco de erros de digitação, inconsistências na sequência do SemVer ou conflitos com versões já publicadas na Microsoft Store. Permitir que o operador selecione o tipo de incremento (`patch`, `minor`, `major` ou `custom`) simplifica a experiência operacional para um único clique, garantindo que o cálculo seja determinístico a partir do estado de desenvolvimento do repositório.

## What Changes

- **Biblioteca Autônoma de Cálculo (`editor/release_tools/calculate_release_version.py`)**: Criação de módulo Library-First com funções puras para inspecionar a versão atual em desenvolvimento (ex: `0.2.1-dev`) e calcular deterministicamente a versão oficial de release baseada no tipo de bump selecionado (`patch`, `minor`, `major` ou `custom`).
- **Test-Driven Development (TDD) com 100% de Cobertura**: Criação de `editor/release_tools/calculate_release_version_test.py` cobrindo todos os cenários válidos, versões com e sem sufixo `-dev`, validações de entrada, tratamento de erros e integração com a CLI.
- **Parametrização do Workflow (`.github/workflows/release-editor.yml`)**:
  - Substituição do input obrigatório de string livre por um menu dropdown (`type: choice`) com opções `patch`, `minor`, `major` e `custom` (com `patch` como padrão).
  - Adição de campo opcional `custom_version` caso o operador selecione o modo `custom`.
  - Adição de etapa inicial no job de release para calcular e exportar a versão via output do GitHub Actions (`steps.versao.outputs.versao`), consumida por todas as etapas subsequentes.

## Capabilities

### New Capabilities
<!-- Nenhuma capability externa criada -->

### Modified Capabilities
- `editor-cicd-pipeline`: Modifica o gatilho de lançamento do editor para suportar seleção de tipo de incremento SemVer (`patch`, `minor`, `major`, `custom`) com cálculo automatizado da versão de release.

## Impact

- **Código modificado**:
  - `editor/release_tools/calculate_release_version.py` (novo)
  - `editor/release_tools/calculate_release_version_test.py` (novo)
  - `.github/workflows/release-editor.yml` (modificado)
- **Operação de CI/CD**:
  - Acionamento mais seguro e ergonômico no portal do GitHub Actions.
