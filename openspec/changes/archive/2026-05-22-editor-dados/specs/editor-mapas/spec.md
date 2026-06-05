## MODIFIED Requirements

### Requirement: Editor de Pontos de Interesse (POI) em Mapas
O sistema SHALL fornecer um editor visual para gerenciar Pontos de Interesse (POI) em mapas de setores e grupos de um croqui, acessível isoladamente ou integrado diretamente no painel principal quando acionado pelo Editor de Dados.

#### Scenario: Acesso Embutido na Árvore de Dados
- **WHEN** o usuário seleciona um nó correspondente a um mapa na árvore do Editor de Dados
- **THEN** o sistema SHALL carregar o `WidgetEditorMapas` na parte direita da área central focando na visualização e edição do mapa e de seus Pontos de Interesse.

#### Scenario: Visualização de mapas disponíveis
- **WHEN** o usuário abre o editor de mapas em modo autônomo ou pela visão "Mapas" da barra lateral
- **THEN** o sistema SHALL listar todos os arquivos de mapa (`.yaml` na pasta `database/`) disponíveis para edição no croqui atual.
