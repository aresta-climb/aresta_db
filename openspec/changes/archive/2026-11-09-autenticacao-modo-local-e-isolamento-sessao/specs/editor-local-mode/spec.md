# Spec Delta

## MODIFIED Requirements

### Requirement: Editor operates directly on local repository
O sistema SHALL permitir a edição nativa e compilação de croquis utilizando a estrutura raiz do repositório local quando inicializado com o caminho do banco de dados (ex: `python editor/main.py database/<id>`), garantindo que a sessão de autenticação do usuário esteja validada antes de abrir a janela de edição.

#### Scenario: Initialization in Local Mode
- **WHEN** o usuário inicia o editor apontando para um croqui na pasta `database/<id>` e já possui uma sessão autenticada válida (ou renovável via refresh token) no cofre de credenciais
- **THEN** o editor valida a sessão, pula a sincronização Git do repositório base em `%APPDATA%` e a tela de seleção (`TelaDeCarregamento`), e abre diretamente a `JanelaPrincipal` com o `LocalRepoWorkspace` e a sessão autenticada ativa

#### Scenario: Initialization in Local Mode without active session
- **WHEN** o usuário inicia o editor apontando para um croqui na pasta `database/<id>` e não possui sessão autenticada válida ou renovável
- **THEN** o editor exibe o fluxo de autenticação na `TelaDeAbertura` e, assim que o login é concluído pelo usuário, abre diretamente a `JanelaPrincipal` com o `LocalRepoWorkspace` sem executar a sincronização Git do repositório base nem abrir a `TelaDeCarregamento`

#### Scenario: Compiling local croqui
- **WHEN** o usuário salva o croqui no modo local
- **THEN** o editor invoca o processo de build para compilar as saídas na pasta correspondente em `generated/<id>` sem criar commits automáticos no git
