# gerenciamento-dependencias-uv Specification

## Purpose
Define a gestão determinística e multiplataforma de dependências Python do repositório `aresta_db` via `uv` (`pyproject.toml` e `uv.lock`), estruturada em grupos modulares para deploy, validação, modo headless e interface gráfica desktop.
## Requirements
### Requirement: Declaração Centralizada de Dependências no pyproject.toml
O repositório MUST definir suas dependências de projeto, restrições de versão do Python e grupos de dependência através de um arquivo `pyproject.toml` na raiz, seguindo os padrões PEP 621 e PEP 735.

#### Scenario: Sincronização padrão de dependências do desenvolvedor
- **WHEN** um desenvolvedor executa `uv sync` na raiz do repositório
- **THEN** o uv cria ou atualiza o ambiente virtual `.venv` com as dependências do projeto e grupos padrão resolvidos de acordo com o `uv.lock`
- **AND** o interpretador Python utilizado respeita a versão especificada em `.python-version` e `requires-python`.

#### Scenario: Sincronização de grupos específicos
- **WHEN** um desenvolvedor ou pipeline executa `uv sync --group editor` ou `uv sync --group deploy`
- **THEN** apenas as dependências do grupo solicitado e as dependências principais são sincronizadas no ambiente virtual.

### Requirement: Versionamento de Lockfile Determinístico Multiplataforma
O repositório MUST manter um arquivo `uv.lock` versionado no Git contendo as versões exatas de todas as dependências transitivas resolvidas para Windows e Linux.

#### Scenario: Resolução multiplataforma com marcadores de sistema
- **WHEN** o comando `uv lock` é executado
- **THEN** o arquivo `uv.lock` é gerado contendo a resolução completa para plataformas `win32` e `linux`, incluindo pacotes específicos do Windows sem quebrar em outros sistemas operacionais.

### Requirement: Execução Padronizada via uv run
Todas as chamadas a scripts Python, ferramentas de build e executores de teste MUST ser realizadas através de `uv run`, assegurando execução no ambiente virtual sincronizado.

#### Scenario: Execução da suíte de testes
- **WHEN** o comando `uv run pytest` é executado
- **THEN** os testes unitários rodam no ambiente virtual gerenciado pelo uv com todas as dependências e variáveis de ambiente configuradas.

#### Scenario: Execução do Editor Aresta
- **WHEN** o comando `uv run editor/main.py` é executado
- **THEN** a interface gráfica do editor é inicializada com o interpretador e bibliotecas corretas.


### Requirement: Grupo de Dependências Enxuto editor_headless Herdado pelo Grupo editor
O arquivo `pyproject.toml` MUST declarar um grupo de dependências `editor_headless` contendo exclusivamente os pacotes necessários para operação *headless* do Editor Aresta e de seu servidor MCP (incluindo o grupo `validador`, `pyside6-essentials`, `pymupdf`, `pillow-heif`, `requests` e dependências do protocolo MCP), e o grupo `editor` MUST herdar `editor_headless` via `{ include-group = "editor_headless" }` acrescentando apenas pacotes exclusivos da interface desktop, cofre de credenciais, telemetria e empacotamento.

#### Scenario: Sincronização enxuta em CI com --only-group editor_headless
- **WHEN** um workflow de integração contínua executa `uv sync --frozen --only-group editor_headless`
- **THEN** o ambiente virtual instala todas as dependências necessárias para executar o Editor Aresta em modo *headless* (incluindo `aresta_renderizar_mapa`, comandos Protobuf e compilação) sem instalar pacotes exclusivos de GUI/distribuição desktop (como `pyinstaller`, `qtawesome`, `keyring` ou `sentry-sdk`)

#### Scenario: Ausência de duplicação no grupo editor completo
- **WHEN** um desenvolvedor executa `uv sync --group editor`
- **THEN** o `uv` resolve todas as dependências de `editor_headless` somadas aos pacotes específicos da interface gráfica sem duplicação de declarações no `pyproject.toml`
