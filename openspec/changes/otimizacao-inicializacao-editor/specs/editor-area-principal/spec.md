## ADDED Requirements

### Requirement: Carregamento Sob Demanda das Visões Secundárias da Janela Principal
A Janela Principal SHALL carregar e instanciar os componentes pesados de suas visões (como o editor interativo de mapas e painéis auxiliares experimentais) sob demanda (lazy loading), instanciando-os somente quando o usuário navegar para a aba correspondente ou quando o recurso for explicitamente habilitado.

#### Scenario: Acesso inicial com página de Dados ativa
- **WHEN** a Janela Principal é exibida inicialmente com a visão de Dados selecionada
- **THEN** os componentes pesados da página de Mapas (`WidgetEditorMapas`) não SHALL ser instanciados previamente na inicialização
- **AND** painéis de abas desativadas ou ocultas (como Betas) não SHALL ser instanciados antecipadamente.

#### Scenario: Navegação para a visão de Mapas
- **WHEN** o usuário clica no ícone "Mapas" na barra lateral pela primeira vez
- **THEN** a página de Mapas SHALL instanciar o componente do editor de mapas sob demanda e integrá-lo à visualização.
