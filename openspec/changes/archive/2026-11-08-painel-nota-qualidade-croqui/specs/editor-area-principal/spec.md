# Spec Delta

## MODIFIED Requirements

### Requirement: Moldura Principal da Janela
A Janela Principal do editor SHALL ser dividida em três regiões distintas: uma barra de ferramentas superior (Top Toolbar), uma barra de ferramentas lateral esquerda (Side Toolbar) e uma área de conteúdo central. A área central atuará como âncora principal para o Painel de qualidade e os editores de dados, imagens e mapas.

#### Scenario: Visualização inicial da Janela Principal
- **WHEN** o aplicativo é inicializado após a seleção de um croqui
- **THEN** a janela principal deve ser exibida com as três áreas visíveis e a área central exibindo inicialmente a página de "Painel" (índice 0), apresentando a `nota_qualidade` e as etapas de tarefas do croqui.

### Requirement: Barra de Ferramentas Lateral (Side Toolbar)
A Side Toolbar SHALL conter ícones premium (via QtAwesome) dispostos verticalmente na lateral esquerda, permitindo alternar entre as visões na ordem: Painel (`fa5s.tachometer-alt`), Dados, Imagens, Mapas, Betas e Histórico.
- **Dimensões**: SHALL possuir 82px de largura total.
- **Botões**: SHALL possuir margens de 6px em todos os lados.

#### Scenario: Seleção de visão na barra lateral
- **WHEN** o usuário clica em um dos ícones da barra lateral (Painel, Dados, Imagens, Mapas, Betas ou Histórico)
- **THEN** o conteúdo da área central SHALL ser atualizado para exibir a visão correspondente.

#### Scenario: Seleção de visão na barra lateral (Painel)
- **WHEN** o usuário clica no ícone de "Painel" na barra lateral
- **THEN** o conteúdo da área central SHALL ser atualizado para exibir o painel de nota de qualidade e tarefas do croqui atual.

#### Scenario: Seleção de visão na barra lateral (Imagens)
- **WHEN** o usuário clica no ícone de "Imagens" na barra lateral
- **THEN** o conteúdo da área central SHALL ser atualizado para exibir o editor de imagens integrado.

#### Scenario: Seleção de visão na barra lateral (Mapas)
- **WHEN** o usuário clica no ícone de "Mapas" na barra lateral
- **THEN** o conteúdo da área central SHALL ser atualizado para exibir o editor de mapas integrado, permitindo a edição visual dos POIs dos mapas do croqui atual.

### Requirement: Carregamento Sob Demanda das Visões Secundárias da Janela Principal
A Janela Principal SHALL carregar e instanciar os componentes pesados de suas visões (como o editor interativo de mapas e painéis auxiliares experimentais) sob demanda (lazy loading), instanciando-os somente quando o usuário navegar para a aba correspondente ou quando o recurso for explicitamente habilitado.

#### Scenario: Acesso inicial com página de Dados ativa
- **WHEN** a Janela Principal é exibida inicialmente com a visão inicial ("Painel" ou "Dados") selecionada
- **THEN** os componentes pesados da página de Mapas (`WidgetEditorMapas`) não SHALL ser instanciados previamente na inicialização
- **AND** painéis de abas desativadas ou ocultas (como Betas) não SHALL ser instanciados antecipadamente.

#### Scenario: Navegação para a visão de Mapas
- **WHEN** o usuário clica no ícone "Mapas" na barra lateral pela primeira vez
- **THEN** a página de Mapas SHALL instanciar o componente do editor de mapas sob demanda e integrá-lo à visualização.
