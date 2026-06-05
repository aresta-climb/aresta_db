## ADDED Requirements

### Requirement: Inicialização da aplicação PyQt6
O aplicativo MUST ser capaz de iniciar uma janela PyQt6 com um layout básico que contenha as opções iniciais, demonstrando o funcionamento do esqueleto do aplicativo.

#### Scenario: App inicia com sucesso
- **WHEN** o usuário executa o aplicativo
- **THEN** uma janela principal é aberta com os botões "Novo croqui", "Importar croqui experimental" e "Editar croqui oficial"
- **THEN** a pasta de dados do usuário é verificada e criada caso não exista

### Requirement: Estrutura local de armazenamento
A aplicação MUST criar e gerenciar um diretório em `local storage` para armazenar o estado do repositório e os croquis experimentais.

#### Scenario: Diretório inexistente no primeiro uso
- **WHEN** o aplicativo é aberto pela primeira vez
- **THEN** cria o diretório de dados do usuário no caminho adequado para o OS usando `QStandardPaths`.

### Requirement: Empacotamento Multiplataforma
O aplicativo MUST poder ser empacotado através do PyInstaller como um executável independente que não exige Python instalado no computador alvo.

#### Scenario: Empacotamento
- **WHEN** o desenvolvedor roda o script de build via PyInstaller
- **THEN** é gerado um artefato executável que abre a GUI sem abrir uma janela de terminal adicional no fundo (via flag `--windowed` ou equivalente).
