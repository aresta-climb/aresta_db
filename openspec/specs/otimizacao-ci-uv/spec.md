## ADDED Requirements

### Requirement: Setup Unificado de Python e Dependências via uv
Os fluxos de CI/CD do GitHub Actions que necessitam de ambiente Python DEVEM utilizar exclusivamente a action `astral-sh/setup-uv@v10` para provisionar tanto o interpretador Python quanto o cache de dependências, dispensando o uso do `actions/setup-python`.

#### Scenario: Execução em ambiente Linux (Ubuntu)
- **WHEN** um workflow de validação (como `pr-db-validator.yml`, `pr-code-validator.yml` ou `pr-integrator.yml`) executa em runner Ubuntu
- **THEN** o passo unificado configura o Python 3.13 e o uv via `astral-sh/setup-uv@v10` com cache de dependências habilitado
- **AND** instala os requisitos via `uv pip install --system`
- **AND** executa a suíte de testes ou script com sucesso.

#### Scenario: Execução em ambiente Windows
- **WHEN** o workflow de lançamento do editor (`release-editor.yml`) executa em runner Windows
- **THEN** o passo unificado configura o Python 3.13 e o uv via `astral-sh/setup-uv@v10` com cache de dependências habilitado
- **AND** instala as dependências via `uv pip install --system`
- **AND** a etapa de empacotamento conclui com sucesso.
