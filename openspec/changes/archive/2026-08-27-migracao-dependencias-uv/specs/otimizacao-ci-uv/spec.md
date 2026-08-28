## MODIFIED Requirements

### Requirement: Setup Unificado de Python e Dependências via uv
Os fluxos de CI/CD do GitHub Actions que necessitam de ambiente Python MUST utilizar a action `astral-sh/setup-uv@v10` combinada com sincronização determinística via `uv sync --frozen` a partir do `uv.lock`, dispensando o uso de `actions/setup-python` e de comandos imperativos de `pip`.

#### Scenario: Execução em ambiente Linux (Ubuntu)
- **WHEN** um workflow de validação (como `pr-db-validator.yml`, `pr-code-validator.yml` ou `pr-integrator.yml`) executa em runner Ubuntu
- **THEN** o passo unificado configura o Python 3.13 e o uv via `astral-sh/setup-uv@v10` com cache habilitado para `uv.lock`
- **AND** sincroniza as dependências de forma determinística via `uv sync --frozen` (com os grupos necessários)
- **AND** executa a suíte de testes ou script através de `uv run` com sucesso.

#### Scenario: Execução em ambiente Windows
- **WHEN** o workflow de lançamento do editor (`release-editor.yml`) executa em runner Windows
- **THEN** o passo unificado configura o Python 3.13 e o uv via `astral-sh/setup-uv@v10` com cache habilitado para `uv.lock`
- **AND** sincroniza as dependências determinísticas via `uv sync --frozen --all-groups`
- **AND** a etapa de testes e empacotamento do executável/MSIX conclui com sucesso.
