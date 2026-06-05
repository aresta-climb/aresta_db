## Why

Para facilitar a criação e iteração de croquis de escalada, os autores locais precisam de uma ferramenta desktop dedicada que permita a edição de croquis e a visualização no aplicativo móvel sem configurar ambientes complexos. Esta mudança inicial foca em criar o esqueleto básico desse editor, com inicialização de diretório de configuração local e uma página inicial com opções para criar, importar ou editar croquis.

## What Changes

- Criação de uma nova pasta `editor` na raiz do repositório para abrigar a aplicação desktop em Python.
- Criação de uma interface gráfica inicial (esqueleto) usando `PyQt6`.
- Configuração de empacotamento em um executável auto-suficiente utilizando `PyInstaller` (alvejando distribuição multiplataforma futuramente).
- Implementação inicial da página principal do editor com a estrutura de pastas local.

## Capabilities

### New Capabilities
- `editor-esqueleto`: Criação do esqueleto da aplicação desktop PyQt6 e sistema de empacotamento via PyInstaller, junto com a página inicial do editor.

### Modified Capabilities

## Impact

- Criação de um novo subprojeto `editor` isolado no repositório `aresta_db`.
- Adição de dependências `PyQt6`, `PyInstaller` e outras bibliotecas auxiliares para o módulo do editor.
