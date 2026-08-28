## MODIFIED Requirements

### Requirement: Inicialização da Aplicação Desktop
A aplicação MUST inicializar e garantir a infraestrutura de pastas locais através de uma Tela de Abertura (Splash Screen) informativa.
O executável principal MUST utilizar o PySide6 (Qt para Python sob licença LGPLv3) para sua interface gráfica, definir explicitamente o nome da aplicação (`QCoreApplication.setApplicationName("EditorAresta")`) e o script de inicialização (`main.py`) MUST iniciar o loop de aplicação do Qt (`QApplication`), instanciando primeiro a `TelaDeAbertura` e, após a inicialização bem-sucedida, a Janela Principal.

#### Scenario: Primeiro uso - Inicialização do repositório
- **WHEN** a aplicação for aberta e a pasta local `%appdata%/EditorAresta` não existir
- **THEN** a aplicação MUST criar a pasta `%appdata%/EditorAresta`
- **THEN** a aplicação MUST realizar o clone do repositório oficial na pasta `%appdata%/EditorAresta/aresta_db` utilizando `pygit2`
- **THEN** a aplicação MUST criar a pasta `%appdata%/EditorAresta/croquis` para armazenamento dos croquis experimentais gerados sob UUIDs aleatórios

#### Scenario: Inicialização subsequente
- **WHEN** a aplicação for aberta e a pasta local `%appdata%/EditorAresta/aresta_db` já existir
- **THEN** a aplicação MUST realizar a sincronização (pull/fetch) do repositório antes de abrir a janela principal
