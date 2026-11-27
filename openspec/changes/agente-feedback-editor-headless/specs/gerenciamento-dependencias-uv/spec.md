# Spec Delta

## ADDED Requirements

### Requirement: Grupo de Dependências Enxuto editor_headless Herdado pelo Grupo editor
O arquivo `pyproject.toml` MUST declarar um grupo de dependências `editor_headless` contendo exclusivamente os pacotes necessários para operação *headless* do Editor Aresta e de seu servidor MCP (incluindo o grupo `validador`, `pyside6-essentials`, `pymupdf`, `pillow-heif`, `requests` e dependências do protocolo MCP), e o grupo `editor` MUST herdar `editor_headless` via `{ include-group = "editor_headless" }` acrescentando apenas pacotes exclusivos da interface desktop, cofre de credenciais, telemetria e empacotamento.

#### Scenario: Sincronização enxuta em CI com --only-group editor_headless
- **WHEN** um workflow de integração contínua executa `uv sync --frozen --only-group editor_headless`
- **THEN** o ambiente virtual instala todas as dependências necessárias para executar o Editor Aresta em modo *headless* (incluindo `aresta_renderizar_mapa`, comandos Protobuf e compilação) sem instalar pacotes exclusivos de GUI/distribuição desktop (como `pyinstaller`, `qtawesome`, `keyring` ou `sentry-sdk`)

#### Scenario: Ausência de duplicação no grupo editor completo
- **WHEN** um desenvolvedor executa `uv sync --group editor`
- **THEN** o `uv` resolve todas as dependências de `editor_headless` somadas aos pacotes específicos da interface gráfica sem duplicação de declarações no `pyproject.toml`
