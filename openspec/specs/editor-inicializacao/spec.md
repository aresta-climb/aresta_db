# editor-inicializacao Specification

## Purpose
TBD - created by archiving change tela-de-abertura. Update Purpose after archive.
## Requirements
### Requirement: Tela de Abertura (Splash Screen) de Inicialização
O Editor Aresta MUST apresentar uma janela de abertura (`TelaDeAbertura`) logo após o início do processo.

#### Scenario: Visualização da Tela de Abertura
- **WHEN** a aplicação for executada
- **THEN** uma janela sem bordas (frameless) MUST ser exibida imediatamente
- **THEN** a janela MUST conter o título "Editor Aresta" e uma barra de progresso estilizada
- **THEN** a barra de progresso MUST ser exibida apenas durante operações de sincronização Git

#### Scenario: Presença e Ícone na Barra de Tarefas do Windows
- **WHEN** a `TelaDeAbertura` for exibida no sistema operacional Windows
- **THEN** a janela MUST ser qualificada na Shell do Windows para exibição na barra de tarefas (estilos `WS_EX_APPWINDOW` e `WS_SYSMENU`)
- **THEN** o botão da aplicação na barra de tarefas MUST exibir imediatamente o ícone oficial da aplicação (`logo_app.png`) e o título "Editor Aresta", sem recorrer ao ícone padrão genérico do sistema operacional

### Requirement: Fluxo de Transição para Janela Principal

A aplicação MUST fechar a `TelaDeAbertura` e abrir a Janela Principal apenas após a conclusão bem-sucedida de todas as etapas de inicialização.

#### Scenario: Inicialização Concluída
- **WHEN** todas as etapas (pastas, autenticação, sincronização) forem concluídas com sucesso
- **THEN** a `TelaDeAbertura` MUST ser fechada
- **THEN** a Janela Principal MUST ser exibida e ganhar o foco do sistema operacional

### Requirement: Tratamento de Falhas na Inicialização
A aplicação MUST informar ao usuário se ocorrer um erro crítico que impeça a abertura do editor.

#### Scenario: Erro de Rede ou Disco
- **WHEN** ocorrer uma falha irrecuperável durante a inicialização
- **THEN** a aplicação MUST ocultar a `TelaDeAbertura` e exibir uma caixa de mensagem de erro crítica
- **THEN** se o erro for 404 em repositório da organização, a mensagem MUST instruir sobre permissões no GitHub

### Requirement: Inicialização Imediata e Imports Sob Demanda
O Editor Aresta SHALL instanciar o `QApplication` e exibir a primeira interface gráfica imediatamente no ciclo de arranque, postergando a importação de submódulos pesados e não essenciais até o momento de sua real necessidade.

#### Scenario: Inicialização em Modo Local Direto
- **WHEN** o editor for iniciado com o caminho de um croqui via argumento de linha de comando
- **THEN** a aplicação SHALL inicializar o `QApplication`, importar estritamente os componentes necessários para a exibição local e apresentar a `JanelaPrincipal` sem importar a tela de login, clientes de autenticação em nuvem ou tarefas de sincronização remota Git.

#### Scenario: Exibição Rápida da Janela de Inicialização Padrão
- **WHEN** o editor for iniciado no fluxo de execução padrão
- **THEN** a aplicação SHALL criar o `QApplication` e exibir a janela de inicialização visual imediatamente
- **THEN** módulos pesados auxiliares SHALL ser importados sob demanda durante as etapas subsequentes do fluxo.

