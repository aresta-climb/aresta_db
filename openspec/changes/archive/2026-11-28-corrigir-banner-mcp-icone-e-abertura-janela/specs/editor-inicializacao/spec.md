# Spec Delta

## MODIFIED Requirements

### Requirement: Tela de Abertura (Splash Screen) de Inicialização
O Editor Aresta MUST apresentar uma janela de abertura (`TelaDeAbertura`) logo após o início do processo gráfico e aplicar de forma determinística a identidade do processo e o ícone do canal nas janelas de nível superior sem efeitos colaterais em tempo de importação.

#### Scenario: Visualização da Tela de Abertura
- **WHEN** a aplicação for executada no modo gráfico
- **THEN** uma janela sem bordas (frameless) MUST ser exibida imediatamente
- **THEN** a janela MUST conter o título do canal ("Editor Aresta" ou "Editor Aresta (Beta)") e uma barra de progresso estilizada
- **THEN** a barra de progresso MUST ser exibida apenas durante operações de sincronização Git

#### Scenario: Presença e Ícone na Barra de Tarefas do Windows
- **WHEN** o Editor Aresta for iniciado em modo gráfico no sistema operacional Windows (inclusive via interpretador Python desempacotado como `uv run`)
- **THEN** a configuração de identidade do processo (`AppUserModelID`) MUST ser invocada apenas durante o arranque gráfico real antes da instanciação do `QApplication`, nunca em tempo de `import` do módulo nem no modo `--headless`
- **THEN** fora de pacotes MSIX, o sistema MUST registrar os metadados visuais do `AppUserModelID` no registro de usuário (`HKCU\Software\Classes\AppUserModelId\<id>`) com `DisplayName` e `IconUri` apontando para o ícone do canal, além de aplicar handles nativos `WM_SETICON` (`ICON_SMALL` e `ICON_BIG`) e atualização de moldura (`SWP_FRAMECHANGED`) nas janelas principais e de abertura
- **THEN** qualquer alteração de `WindowFlags` em janelas/diálogos (como `TelaDeAbertura` e `TelaDeCarregamento`) MUST preceder ou reaplicar `setWindowIcon`, exibindo sempre o ícone oficial do Aresta na janela e na barra de tarefas

### Requirement: Fluxo de Transição para Janela Principal
A aplicação MUST preservar o loop principal de eventos (`app.exec()`) ativo durante todas as transições entre `TelaDeAbertura`, `TelaDeCarregamento` e `JanelaPrincipal`, realizando a carga pesada do croqui em segundo plano antes de ocultar a janela anterior para eliminar lacunas sem janela visível.

#### Scenario: Inicialização Concluída
- **WHEN** todas as etapas de inicialização (pastas, cofre, autenticação, sincronização Git e pré-aquecimento de módulos pesados) forem concluídas com sucesso no modo padrão (sem caminho de croqui local)
- **THEN** a `TelaDeAbertura` MUST ser fechada e a `TelaDeCarregamento` MUST ser exibida mantendo o loop principal de eventos ativo

#### Scenario: Inicialização Concluída no Modo Local Direto
- **WHEN** o editor for iniciado informando um caminho de croqui local via linha de comando
- **THEN** a `TarefaInicializacao` MUST pré-aquecer os módulos pesados e executar em segundo plano o carregamento completo do croqui (migrações, YAML, arquivos externos `.md`/`curadoria_betas.yaml`, `commit_base_sha` e avaliação inicial da `nota_qualidade`) enquanto a `TelaDeAbertura` permanece visível com status atualizado
- **THEN** ao concluir a tarefa, a `JanelaPrincipal` MUST receber o pacote pré-carregado, ser exibida imediatamente com `LocalRepoWorkspace` e fechar a `TelaDeAbertura` sem intervalo sem janela visível

#### Scenario: Abertura de Croqui Oficial, Novo ou Existente a partir da Tela de Carregamento
- **WHEN** o usuário (ou agente via MCP) cria um novo croqui, importa um croqui oficial ou seleciona um croqui do histórico na `TelaDeCarregamento` e o diálogo é aceito
- **THEN** o carregamento pesado do croqui MUST ocorrer fora da thread de interface gráfica antes da transição final e a `JanelaPrincipal` MUST ser exibida imediatamente com o pacote hidratado, mantendo o loop principal de eventos ativo

#### Scenario: Retorno da Janela Principal para a Tela de Carregamento via Abrir Novo
- **WHEN** o usuário aciona a opção "Abrir Novo" na `JanelaPrincipal` para selecionar outro croqui
- **THEN** a `JanelaPrincipal` anterior MUST ser fechada e a `TelaDeCarregamento` MUST ser reaberta sem encerrar o loop principal de eventos da aplicação

### Requirement: Inicialização Imediata e Imports Sob Demanda
O Editor Aresta SHALL instanciar o `QApplication` e exibir a primeira interface gráfica imediatamente no ciclo de arranque, pré-aquecendo os módulos pesados em thread de segundo plano durante a `TarefaInicializacao`.

#### Scenario: Inicialização em Modo Local Direto
- **WHEN** o editor for iniciado com o caminho de um croqui via argumento de linha de comando
- **THEN** a aplicação SHALL validar o caminho do croqui local imediatamente e delegar ao `ControladorAplicativo` com `sincronizar_git=False`, executando verificação de sessão, pré-aquecimento de módulos e hidratação do croqui em segundo plano antes de apresentar a `JanelaPrincipal` sem sincronização remota Git do repositório base nem `TelaDeCarregamento`

#### Scenario: Exibição Rápida da Janela de Inicialização Padrão
- **WHEN** o editor for iniciado no fluxo de execução padrão
- **THEN** a aplicação SHALL criar o `QApplication` e exibir a `TelaDeAbertura` imediatamente
- **THEN** módulos pesados da área principal SHALL ser pré-aquecidos em segundo plano durante a `TarefaInicializacao` sem bloquear a thread de UI.
