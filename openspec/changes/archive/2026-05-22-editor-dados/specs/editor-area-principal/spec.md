## MODIFIED Requirements

### Requirement: Moldura Principal da Janela
A Janela Principal do editor SHALL ser dividida em três regiões distintas: uma barra de ferramentas superior (Top Toolbar), uma barra de ferramentas lateral esquerda (Side Toolbar) e uma área de conteúdo central. A área central atuará como âncora principal para os editores de dados, imagens e mapas gerenciados pelo roteamento do "Editor de Dados".

#### Scenario: Visualização inicial da Janela Principal
- **WHEN** o aplicativo é inicializado após a seleção de um croqui
- **THEN** a janela principal deve ser exibida com as três áreas visíveis e a área central exibindo inicialmente a página de "Dados", carregando a visão de árvore na lateral esquerda dessa área central.
