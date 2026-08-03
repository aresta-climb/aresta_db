## ADDED Requirements

### Requirement: Editor operates directly on local repository
O sistema DEVE permitir a edição nativa e compilação de croquis utilizando a estrutura raiz do repositório local quando inicializado com o caminho do banco de dados (ex: `python editor/main.py database/<id>`).

#### Scenario: Initialization in Local Mode
- **WHEN** o usuário inicia o editor apontando para um croqui na pasta database
- **THEN** o editor carrega o croqui sem exibir telas de login, sincronização ou seleção

#### Scenario: Compiling local croqui
- **WHEN** o usuário salva o croqui no modo local
- **THEN** o editor invoca o processo de build para compilar as saídas na pasta correspondente em `generated/<id>` sem criar commits automáticos no git

### Requirement: Workspace interface for path and storage abstraction
O sistema DEVE abstrair as operações de arquivo e git (salvar, compilar, obter caminho do database) atrás de uma interface polimórfica (Workspace) para permitir que a UI (`JanelaPrincipal`) permaneça agnóstica à topologia de pastas do croqui (Experimental vs. Local Repo).

#### Scenario: Saving maps and images
- **WHEN** a `JanelaPrincipal` solicita salvar as alterações do croqui
- **THEN** o Workspace resolve o caminho `caminho_database` apropriado (diretório `database` para experimental, ou o diretório raiz do croqui em local) e persiste as modificações.

### Requirement: Safely rename local croqui ID
O sistema DEVE sincronizar a renomeação do ID de um croqui na UI com o sistema de arquivos local de modo seguro.

#### Scenario: Renaming croqui ID in Local Mode
- **WHEN** o usuário altera o ID de um croqui na UI e salva
- **THEN** o sistema utiliza `git mv` para renomear as pastas `database/<id_antigo>` e `generated/<id_antigo>` para o novo ID, mantendo o histórico de versão do git.

### Requirement: Distinct UI for Local Mode
O sistema DEVE prover indicativos visuais de que o aplicativo está rodando em modo de Repositório Local.

#### Scenario: App window displays Local Mode
- **WHEN** a `JanelaPrincipal` for carregada utilizando o `LocalRepoWorkspace`
- **THEN** o título da janela ou a barra superior deve exibir claramente a tag "Local Mode" (ex: `Editor Aresta - [Local Mode] - Nome do Croqui`)

#### Scenario: Publish button is disabled
- **WHEN** a `JanelaPrincipal` for carregada utilizando o `LocalRepoWorkspace`
- **THEN** o botão "Publicar" deve ficar visível na barra de ferramentas, porém desabilitado (cinza)

### Requirement: TDD and Test Coverage
Todo o código desenvolvido para esta funcionalidade DEVE seguir a metodologia Test-Driven Development (TDD) e manter 100% de cobertura de testes unitários.

#### Scenario: Validating coverage for Workspace
- **WHEN** novos testes são executados (`pytest`) para o módulo `editor/core/workspace.py`
- **THEN** o relatório de cobertura deve indicar 100% de linhas testadas para as classes do workspace.
