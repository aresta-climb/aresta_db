## Why

O editor Aresta é uma ferramenta desktop auxiliar desenhada para facilitar a criação e iteração de croquis de escalada. Atualmente, criar e editar croquis requer configurar ambientes de desenvolvimento e mexer diretamente com arquivos complexos. Esta mudança resolve o problema criando um aplicativo amigável, onde autores podem editar e testar os croquis de forma nativa e simples. O objetivo inicial é construir o esqueleto da aplicação e sua página inicial, estabelecendo a base sobre a qual as futuras funcionalidades de edição e integração com o GitHub serão construídas.

## What Changes

- Criação de um novo projeto na pasta `editor/` na raiz do repositório.
- Configuração do aplicativo desktop em Python utilizando PyQt6 para a interface gráfica.
- Configuração do empacotamento do aplicativo como executável auto-suficiente via PyInstaller.
- Implementação da lógica de inicialização, que gerencia o armazenamento local (app data ou similar) e garante a presença do último commit do repositório `aresta_db` localmente.
- Implementação da Página Inicial dividida em opções de gerenciamento de croquis (Novo croqui, Importar croqui experimental e Editar croqui oficial) e listagem de croquis experimentais já em edição.
- Implementação da estrutura de pastas para os croquis experimentais no disco local.

## Capabilities

### New Capabilities

- `editor-arquitetura`: Define a arquitetura base da ferramenta desktop, tecnologias envolvidas (PyQt6, PyInstaller), formatação e inicialização do diretório local do usuário.
- `editor-pagina-inicial`: Define a interface e fluxos da tela inicial, incluindo listagem de croquis experimentais, fluxo de novo croqui, importação e edição oficial.

### Modified Capabilities

Nenhuma capacidade existente será modificada, pois trata-se de um novo módulo.

## Impact

- Criação do diretório isolado `editor/` na raiz do projeto.
- Inclusão de novas dependências (ex: `PyQt6`, `PyInstaller`, bibliotecas do `git`) para a ferramenta desktop.
- Nenhuma alteração no código atual do backend Python do projeto aresta_db ou na API do Flutter, visto que a ferramenta consome e produz os arquivos padrão.
