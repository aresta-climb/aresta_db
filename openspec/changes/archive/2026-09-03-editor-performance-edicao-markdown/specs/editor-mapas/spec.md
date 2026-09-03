## MODIFIED Requirements

### Requirement: Editor de Pontos de Interesse (POI) em Mapas
O sistema SHALL fornecer um editor visual para gerenciar Pontos de Interesse (POI) e Referências em mapas de setores e grupos de um croqui, acessível primariamente integrado no painel principal em sua própria aba, respondendo a comandos da QUndoStack global e lendo diretamente do `CroquiModel`. A interface SHALL ser estruturada em três painéis horizontais (Mapas à esquerda, Visualizador ao centro, Referências à direita). O Visualizador ao centro SHALL suportar navegação através do arrasto da visualização (panning) quando o usuário clicar e arrastar no fundo da imagem (fora dos POIs). O editor visual SHALL suportar a renderização, criação e manipulação das geometrias `circulo`, `quadrado`, `retangulo` e `poligono`.
- **Filtragem Reativa da Lista de Mapas**: O sistema SHALL reconstruir a lista de mapas na barra lateral apenas em resposta a alterações estruturais ou mutações que afetem mensagens de mapas, ignorando eventos de alteração de campos puramente textuais (como descrições e conteúdos markdown).

#### Scenario: Acesso Embutido na Árvore de Dados
- **WHEN** o usuário seleciona um nó correspondente a um mapa na árvore do Editor de Dados e clica para abri-lo
- **THEN** o sistema SHALL carregar a aba de mapas na JanelaPrincipal, focando na visualização e edição do mapa e de seus Pontos de Interesse, com o estado sincronizado pelo `CroquiModel`.

#### Scenario: Visualização de mapas disponíveis
- **WHEN** o usuário abre a aba do editor de mapas
- **THEN** o sistema SHALL listar, na barra lateral, todos os mapas (`Mapa` protobuf messages) disponíveis na hierarquia do `CroquiModel` carregado.

#### Scenario: Arrasto da visualização pelo fundo do mapa
- **WHEN** o usuário clica em uma área do mapa (Visualizador) que não contém um POI e arrasta o cursor
- **THEN** o sistema SHALL mover a visualização do mapa (panning) correspondente ao movimento do mouse

#### Scenario: Manipulação de Quadrados e Polígonos
- **WHEN** o usuário visualiza ou interage com um mapa que possua os novos formatos de POI
- **THEN** o sistema SHALL renderizar adequadamente `quadrado` e `poligono` no visualizador

#### Scenario: Rejeição de Atualização da Lista por Alteração Textual
- **WHEN** um campo textual (`conteudo`, `descricao`, etc.) for alterado no modelo
- **THEN** o Editor de Mapas não deve reconstruir a lista lateral de mapas.
