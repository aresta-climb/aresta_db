# editor-arquitetura Specification

## Purpose
Arquitetura base do Editor Aresta, definindo os processos de inicialização e interface.
## Requirements
### Requirement: Inicialização da Aplicação Desktop
A aplicação MUST inicializar e garantir a infraestrutura de pastas locais através de uma Tela de Abertura (Splash Screen) informativa.
O executável principal MUST utilizar o PyQt6 para sua interface gráfica, e o script de inicialização (`main.py`) MUST iniciar o loop de aplicação do Qt (`QApplication`), instanciando primeiro a `TelaDeAbertura` e, após a inicialização bem-sucedida, a Janela Principal.

#### Scenario: Primeiro uso - Inicialização do repositório
- **WHEN** a aplicação for aberta e a pasta local `%appdata%/aresta_editor` não existir
- **THEN** a aplicação MUST criar a pasta `%appdata%/aresta_editor`
- **THEN** a aplicação MUST realizar o clone do repositório oficial na pasta `%appdata%/aresta_editor/aresta_db` utilizando `pygit2`
- **THEN** a aplicação MUST criar a pasta `%appdata%/aresta_editor/croquis_experimentais`

#### Scenario: Inicialização subsequente
- **WHEN** a aplicação for aberta e a pasta local `%appdata%/aresta_editor/aresta_db` já existir
- **THEN** a aplicação MUST realizar a sincronização (pull/fetch) do repositório antes de abrir a janela principal

### Requirement: Formato da Janela Principal
A aplicação MUST apresentar uma janela gráfica interativa.

#### Scenario: Interface Base
- **WHEN** a aplicação inicializar
- **THEN** a aplicação MUST apresentar uma janela (`QMainWindow`) contendo uma barra lateral esquerda e uma área principal à direita (via `QSplitter` ou layouts similares)
- **THEN** a aplicação NÃO MUST finalizar imediatamente

### Requirement: Empacotamento
A aplicação MUST prover scripts de build para empacotamento standalone.

#### Scenario: Geração de Executável
- **WHEN** o desenvolvedor rodar o script de empacotamento
- **THEN** o script MUST invocar o PyInstaller para gerar um único executável/app (`.exe`, `.AppImage` ou `.app` a depender do SO) que rode a aplicação sem necessitar de bibliotecas Python pré-instaladas.

