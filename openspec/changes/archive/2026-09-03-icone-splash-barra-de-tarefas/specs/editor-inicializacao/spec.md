## MODIFIED Requirements

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
