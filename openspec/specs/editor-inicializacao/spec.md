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

