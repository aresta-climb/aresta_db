## MODIFIED Requirements

### Requirement: Editor de Pontos de Interesse (POI) em Mapas
O sistema SHALL fornecer um editor visual para gerenciar Pontos de Interesse (POI) em mapas de setores e grupos de um croqui, acessível primariamente integrado no painel principal em sua própria aba, respondendo a comandos da QUndoStack global e lendo diretamente do `CroquiModel`.

#### Scenario: Acesso Embutido na Árvore de Dados
- **WHEN** o usuário seleciona um nó correspondente a um mapa na árvore do Editor de Dados e clica para abri-lo
- **THEN** o sistema SHALL carregar a aba de mapas na JanelaPrincipal, focando na visualização e edição do mapa e de seus Pontos de Interesse, com o estado sincronizado pelo `CroquiModel`.

#### Scenario: Visualização de mapas disponíveis
- **WHEN** o usuário abre a aba do editor de mapas
- **THEN** o sistema SHALL listar, na barra lateral, todos os mapas (`Mapa` protobuf messages) disponíveis na hierarquia do `CroquiModel` carregado.
