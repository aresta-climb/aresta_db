# Spec Delta

## MODIFIED Requirements

### Requirement: Carregamento Sob Demanda das Visões Secundárias da Janela Principal
A Janela Principal SHALL abrir na aba inicial ("Painel") reutilizando dados pré-carregados quando fornecidos, instanciando sob demanda (*lazy loading*) os componentes pesados das abas secundárias (**Dados**, **Imagens**, **Mapas** e **Betas**) apenas quando o usuário navegar até elas ou quando uma ação de foco/MCP exigir acesso direto, e iniciando o servidor MCP sem bloquear a thread principal.

#### Scenario: Acesso inicial com página de Dados ativa
- **WHEN** a `JanelaPrincipal` é exibida inicialmente com a visão inicial ("Painel") selecionada
- **THEN** os componentes pesados das abas secundárias (`WidgetEditorDados`, `WidgetEditorImagens`, `WidgetEditorMapas` e `PainelCuradoria`) NÃO SHALL ser instanciados nem decodificar imagens na abertura inicial
- **AND** se um pacote de croqui pré-carregado com `ResultadoNotaQualidade` for fornecido, o painel inicial SHALL renderizar diretamente sem reexecutar I/O de disco nem `git rev-parse` na thread de UI
- **AND** caso existam alterações pendentes de recuperação no diário (`diario_pendente.bin`), o `DialogoRecuperacaoSessao` SHALL ser exibido somente após a `JanelaPrincipal` já estar visível na tela com seu ícone aplicado.

#### Scenario: Navegação para a visão de Mapas
- **WHEN** o usuário clica no ícone "Dados", "Imagens", "Mapas" ou "Betas" na barra lateral pela primeira vez, ou quando uma navegação de contexto/ferramenta MCP solicita o widget daquela página
- **THEN** a página correspondente SHALL instanciar seu editor sob demanda, hidratá-lo com o `CroquiModel` e `CroquiController` ativos e integrá-lo imediatamente à visualização.

#### Scenario: Partida não-bloqueante do ServidorMCP na abertura da janela
- **WHEN** a `JanelaPrincipal` inicializa o `ServidorMCP` com `iniciar_rede=True` durante a abertura da janela
- **THEN** o catálogo de ferramentas do croqui MUST ser registrado uma única vez por carregamento e o servidor Uvicorn MUST vincular o socket/gravar a sessão imediatamente e iniciar sua thread em segundo plano sem bloquear a thread de UI em loops de espera (`sleep`).
