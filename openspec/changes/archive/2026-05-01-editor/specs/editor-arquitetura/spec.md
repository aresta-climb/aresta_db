## ADDED Requirements

### Requirement: Inicialização da Aplicação Desktop
A aplicação DEVE inicializar e garantir a infraestrutura de pastas locais.
O executável principal DEVE utilizar o PyQt6 para sua interface gráfica, e o script de inicialização (`main.py`) DEVE iniciar o loop de aplicação do Qt (`QApplication`).

#### Scenario: Primeiro uso - Inicialização do repositório
- **WHEN** a aplicação for aberta e a pasta local `%appdata%/aresta_editor` não existir
- **THEN** a aplicação DEVE criar a pasta `%appdata%/aresta_editor`
- **THEN** a aplicação DEVE realizar o clone do repositório oficial na pasta `%appdata%/aresta_editor/base_repo`
- **THEN** a aplicação DEVE criar a pasta `%appdata%/aresta_editor/croquis_experimentais`

#### Scenario: Inicialização subsequente
- **WHEN** a aplicação for aberta e a pasta local `%appdata%/aresta_editor/base_repo` já existir
- **THEN** a aplicação DEVE acessar a pasta sem efetuar um novo clone

### Requirement: Formato da Janela Principal
A aplicação DEVE apresentar uma janela gráfica interativa.

#### Scenario: Interface Base
- **WHEN** a aplicação inicializar
- **THEN** a aplicação DEVE apresentar uma janela (`QMainWindow`) contendo uma barra lateral esquerda e uma área principal à direita (via `QSplitter` ou layouts similares)
- **THEN** a aplicação NÃO DEVE finalizar imediatamente

### Requirement: Empacotamento
A aplicação DEVE prover scripts de build para empacotamento standalone.

#### Scenario: Geração de Executável
- **WHEN** o desenvolvedor rodar o script de empacotamento
- **THEN** o script DEVE invocar o PyInstaller para gerar um único executável/app (`.exe`, `.AppImage` ou `.app` a depender do SO) que rode a aplicação sem necessitar de bibliotecas Python pré-instaladas.
