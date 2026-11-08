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

A aplicação MUST preservar o loop principal de eventos (`app.exec()`) ativo durante todas as transições entre a `TelaDeAbertura`, a `TelaDeCarregamento` e a `JanelaPrincipal`, fechando a janela anterior e exibindo a próxima sem disparar o encerramento automático do aplicativo por ausência temporária de janelas visíveis. O processo só MUST encerrar quando o usuário cancelar explicitamente a `TelaDeCarregamento` (sem logout em andamento) ou fechar todas as janelas principais abertas.

#### Scenario: Inicialização Concluída
- **WHEN** todas as etapas de inicialização (pastas, autenticação, sincronização) forem concluídas com sucesso
- **THEN** a `TelaDeAbertura` MUST ser fechada e a `TelaDeCarregamento` MUST ser exibida mantendo o loop principal de eventos ativo

#### Scenario: Abertura de Croqui Oficial, Novo ou Existente a partir da Tela de Carregamento
- **WHEN** o usuário (ou agente via MCP) cria um novo croqui, importa um croqui oficial ou seleciona um croqui do histórico na `TelaDeCarregamento` e o diálogo é aceito
- **THEN** a `JanelaPrincipal` MUST ser instanciada com o croqui selecionado, exibida na tela e mantida viva no loop principal de eventos (`app.exec()`), sem que o fechamento intermediário da `TelaDeCarregamento` dispare `aboutToQuit` ou encerre a aplicação

#### Scenario: Retorno da Janela Principal para a Tela de Carregamento via Abrir Novo
- **WHEN** o usuário aciona a opção "Abrir Novo" na `JanelaPrincipal` para selecionar outro croqui
- **THEN** a `JanelaPrincipal` anterior MUST ser fechada e a `TelaDeCarregamento` MUST ser reaberta sem encerrar o loop principal de eventos da aplicação

### Requirement: Tratamento de Falhas na Inicialização
A aplicação MUST informar ao usuário se ocorrer um erro crítico que impeça a abertura do editor e MUST continuar a inicialização em modo offline caso a falha de sincronização remota ocorra sobre uma base local já existente.

#### Scenario: Erro de Rede ou Disco
- **WHEN** ocorrer uma falha irrecuperável durante a inicialização
- **THEN** a aplicação MUST ocultar a `TelaDeAbertura` e exibir uma caixa de mensagem de erro crítica
- **THEN** se o erro for 404 em repositório da organização, a mensagem MUST instruir sobre permissões no GitHub

#### Scenario: Falha Não Crítica de Sincronização com Base Existente
- **WHEN** ocorrer uma falha de conexão de rede durante a sincronização de dados remotos e a base local de croquis já existir no disco
- **THEN** a aplicação MUST registrar um aviso no log e emitir atualização de status na interface
- **THEN** a aplicação MUST prosseguir normalmente com a inicialização e abrir o editor utilizando os dados locais

### Requirement: Inicialização Imediata e Imports Sob Demanda
O Editor Aresta SHALL instanciar o `QApplication` e exibir a primeira interface gráfica imediatamente no ciclo de arranque, postergando a importação de submódulos pesados e não essenciais até o momento de sua real necessidade.

#### Scenario: Inicialização em Modo Local Direto
- **WHEN** o editor for iniciado com o caminho de um croqui via argumento de linha de comando
- **THEN** a aplicação SHALL inicializar o `QApplication`, importar estritamente os componentes necessários para a exibição local e apresentar a `JanelaPrincipal` sem importar a tela de login, clientes de autenticação em nuvem ou tarefas de sincronização remota Git.

#### Scenario: Exibição Rápida da Janela de Inicialização Padrão
- **WHEN** o editor for iniciado no fluxo de execução padrão
- **THEN** a aplicação SHALL criar o `QApplication` e exibir a janela de inicialização visual imediatamente
- **THEN** módulos pesados auxiliares SHALL ser importados sob demanda durante as etapas subsequentes do fluxo.

### Requirement: Etapa de Desbloqueio do Cofre de Senhas na Inicialização
A `TarefaInicializacao` da Splash Screen MUST incluir uma etapa formal de inicialização e desbloqueio do cofre de credenciais do sistema operacional executada em segundo plano antes da verificação de sessão.

#### Scenario: Notificação Visual e Desbloqueio em Segundo Plano
- **WHEN** a `TarefaInicializacao` iniciar a etapa de acesso ao cofre de senhas
- **THEN** a interface gráfica MUST atualizar a barra de progresso e exibir o status "Acessando cofre de senhas do aplicativo..."
- **AND** a aplicação MUST aguardar uma breve pausa para leitura do usuário antes de disparar a solicitação ao cofre no sistema operacional
- **AND** a requisição MUST ser executada em thread separada da interface gráfica para manter a janela responsiva

#### Scenario: Desbloqueio Concluído com Sucesso
- **WHEN** o cofre do sistema estiver destrancado ou o usuário fornecer a senha com sucesso no diálogo nativo
- **THEN** a aplicação MUST registrar o cofre como operacional e prosseguir para a verificação de autenticação

#### Scenario: Desbloqueio Cancelado pelo Usuário
- **WHEN** o usuário cancelar explicitamente o diálogo de senha do sistema operacional
- **THEN** a aplicação MUST registrar o cofre como não operacional, ativar a retenção de sessão temporária em memória RAM e prosseguir com a inicialização
