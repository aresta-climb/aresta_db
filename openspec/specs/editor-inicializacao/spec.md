# editor-inicializacao Specification

## Purpose
Define o fluxo de inicialização do Editor Aresta (`TelaDeAbertura`, autenticação, cofre de senhas, sincronização Git, registro do servidor MCP, transições seguras entre janelas sem processos zumbis e modo de autoverificação `--smoke-test`).

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
- **WHEN** todas as etapas de inicialização (pastas, cofre, autenticação e sincronização Git) forem concluídas com sucesso no modo padrão (sem caminho de croqui local)
- **THEN** a `TelaDeAbertura` MUST ser fechada e a `TelaDeCarregamento` MUST ser exibida mantendo o loop principal de eventos ativo

#### Scenario: Inicialização Concluída no Modo Local Direto
- **WHEN** as etapas de inicialização do modo local (pastas, cofre e autenticação, sem sincronização Git do repositório base) forem concluídas com sucesso para um caminho de croqui local informado via linha de comando
- **THEN** a `TelaDeAbertura` MUST ser fechada e a `JanelaPrincipal` MUST ser instanciada diretamente com `LocalRepoWorkspace` e o `GerenciadorSessao` autenticado, mantendo o loop principal de eventos ativo

#### Scenario: Abertura de Croqui Oficial, Novo ou Existente a partir da Tela de Carregamento
- **WHEN** o usuário (ou agente via MCP) cria um novo croqui, importa um croqui oficial ou seleciona um croqui do histórico na `TelaDeCarregamento` e o diálogo é aceito
- **THEN** a `JanelaPrincipal` MUST ser instanciada com o croqui selecionado, exibida na tela e mantida viva no loop principal de eventos (`app.exec()`), sem que o fechamento intermediário da `TelaDeCarregamento` dispare `aboutToQuit` ou encerre a aplicação

#### Scenario: Retorno da Janela Principal para a Tela de Carregamento via Abrir Novo
- **WHEN** o usuário aciona a opção "Abrir Novo" na `JanelaPrincipal` para selecionar outro croqui
- **THEN** a `JanelaPrincipal` anterior MUST ser fechada e a `TelaDeCarregamento` MUST ser reaberta sem encerrar o loop principal de eventos da aplicação

### Requirement: Tratamento de Falhas na Inicialização
A aplicação MUST informar ao usuário se ocorrer um erro crítico que impeça a abertura do editor (inclusive durante a transição da `TelaDeAbertura` para a `TelaDeCarregamento` ou `JanelaPrincipal`), encerrando limpo o processo e liberando as travas locais de seleção ou de croqui sem deixar processos invisíveis em segundo plano, e MUST continuar a inicialização em modo offline caso a falha de sincronização remota ocorra sobre uma base local já existente.

#### Scenario: Erro de Rede ou Disco
- **WHEN** ocorrer uma falha irrecuperável durante a inicialização
- **THEN** a aplicação MUST ocultar a `TelaDeAbertura` e exibir uma caixa de mensagem de erro crítica
- **THEN** se o erro for 404 em repositório da organização, a mensagem MUST instruir sobre permissões no GitHub

#### Scenario: Falha Não Crítica de Sincronização com Base Existente
- **WHEN** ocorrer uma falha de conexão de rede durante a sincronização de dados remotos e a base local de croquis já existir no disco
- **THEN** a aplicação MUST registrar um aviso no log e emitir atualização de status na interface
- **THEN** a aplicação MUST prosseguir normalmente com a inicialização e abrir o editor utilizando os dados locais

#### Scenario: Exceção Crítica Após Fechamento da Tela de Abertura na Transição de Janelas
- **WHEN** ocorrer uma exceção inesperada durante a abertura da `TelaDeCarregamento`, registro do servidor MCP ou instanciação da `JanelaPrincipal` após o fechamento da `TelaDeAbertura`
- **THEN** a aplicação MUST capturar e registrar a exceção na telemetria, exibir uma caixa de mensagem crítica visível ao usuário (exceto em modo `--smoke-test` automatizado), encerrar os servidores locais e finalizar o loop de eventos para não manter um processo zumbi sem janelas.

### Requirement: Inicialização Imediata e Imports Sob Demanda
O Editor Aresta SHALL instanciar o `QApplication` e exibir a primeira interface gráfica imediatamente no ciclo de arranque, postergando a importação de submódulos pesados e não essenciais até o momento de sua real necessidade.

#### Scenario: Inicialização em Modo Local Direto
- **WHEN** o editor for iniciado com o caminho de um croqui via argumento de linha de comando
- **THEN** a aplicação SHALL validar o caminho do croqui local imediatamente e delegar ao `ControladorAplicativo` com `sincronizar_git=False`, executando apenas a verificação/autenticação de sessão antes de apresentar a `JanelaPrincipal` sem importar ou executar a sincronização remota Git do repositório base nem a `TelaDeCarregamento`

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

### Requirement: Registro Obrigatório do Servidor MCP no Ciclo de Vida da Aplicação
O Editor Aresta MUST instanciar o servidor MCP e registrar integralmente todas as ferramentas MCP globais e de edição durante a abertura da `TelaDeCarregamento` e da `JanelaPrincipal` em qualquer execução da aplicação ou suíte de testes, permitindo suprimir exclusivamente a abertura de porta TCP de rede (`iniciar_rede_mcp=False`) em testes automatizados em memória.

#### Scenario: Registro integral de ferramentas MCP mesmo sem abertura de rede
- **WHEN** a aplicação ou uma suíte de testes (incluindo o Robô Caótico) inicializa o fluxo de `TelaDeCarregamento` ou `JanelaPrincipal` com `iniciar_rede_mcp=False`
- **THEN** o servidor MCP MUST ser instanciado e todas as ferramentas MCP (conhecimento, gestão de croquis/PDF, comandos, visão e curadoria de betas) MUST ser importadas e registradas em memória sem abrir socket TCP.

### Requirement: Modo de Autoverificação Ponta a Ponta Offline (--smoke-test)
O executável do Editor Aresta MUST suportar um modo de autoverificação automatizada acionado via linha de comando (`--smoke-test`) que percorre o fluxo completo de produção sem mocks internos e sem acesso à internet externa, validando login OTP, sincronização Git local, servidor MCP HTTP, abertura/criação de croqui na janela principal, particionamento de PDF, parser de busca web e compilação/salvamento.

#### Scenario: Execução bem-sucedida do smoke test no pacote compilado
- **WHEN** o binário empacotado do Editor Aresta é iniciado com `--smoke-test` apontando para um servidor HTTP local de autenticação e um repositório Git local em diretório temporário isolado
- **THEN** a aplicação MUST completar o login por código OTP na `TelaDeAbertura`, sincronizar o repositório Git, iniciar o servidor MCP HTTP na `TelaDeCarregamento`, abrir um croqui na `JanelaPrincipal`, particionar um arquivo PDF em imagens WebP, validar o carregamento do extrator HTML de betas, salvar/compilar o croqui e encerrar com código de saída `0`.

#### Scenario: Falha imediata em caso de dependência nativa ausente no smoke test
- **WHEN** o binário empacotado iniciado com `--smoke-test` encontra qualquer exceção não tratada, falha de importação ou erro de execução em alguma etapa
- **THEN** o processo MUST registrar o erro em `stderr` e encerrar imediatamente com código de saída diferente de zero sem travar em diálogos modais.

### Requirement: Trava de Instância Escopada por Seleção e por Croqui
O Editor Aresta MUST substituir a trava global única por uma trava dedicada à tela de seleção (`ArestaEditorTelaSelecao`) e uma trava escopada por croqui (`ArestaEditorCroqui_<id_croqui>`), permitindo a execução simultânea de múltiplas instâncias independentes em croquis distintos.

#### Scenario: Abertura simultânea de croquis distintos via linha de comando
- **WHEN** uma primeira instância do editor está executando com o croqui `"A"` e o usuário executa um segundo processo informando o croqui `"B"` diferente de `"A"`
- **THEN** o segundo processo MUST validar o caminho de `"B"` antes da checagem de instância, adquirir a trava `ArestaEditorCroqui_B` e abrir normalmente uma segunda `JanelaPrincipal` independente

#### Scenario: Bloqueio e elevação ao tentar reabrir o mesmo croqui via linha de comando
- **WHEN** o croqui `"A"` já está aberto em uma janela ativa e o usuário executa outro processo informando o mesmo croqui `"A"`
- **THEN** o segundo processo MUST detectar a trava `ArestaEditorCroqui_A` responsiva, trazer especificamente a janela de `"A"` para o primeiro plano, informar ao usuário que o croqui já está aberto e encerrar com código `0`

#### Scenario: Bloqueio de tela de seleção duplicada e liberação após abertura de croqui
- **WHEN** uma instância está aguardando seleção na `TelaDeCarregamento` sem croqui aberto e outro processo é iniciado sem argumentos de croqui
- **THEN** o segundo processo MUST elevar a `TelaDeCarregamento` existente e encerrar; assim que o primeiro processo abrir um croqui na `JanelaPrincipal`, a trava de seleção MUST ser liberada para que novas instâncias possam abrir outra `TelaDeCarregamento`
