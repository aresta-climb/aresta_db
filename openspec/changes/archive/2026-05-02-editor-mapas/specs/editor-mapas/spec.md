## Purpose
Fornecer um editor visual para gerenciar Pontos de Interesse (POI) em mapas de setores e grupos.

## ADDED Requirements

### Requirement: Editor de Pontos de Interesse (POI) em Mapas
O sistema SHALL fornecer um editor visual para gerenciar Pontos de Interesse (POI) em mapas de setores e grupos de um croqui.

#### Scenario: Visualização de mapas disponíveis
- **WHEN** o usuário abre o editor de mapas
- **THEN** o sistema SHALL listar todos os arquivos de mapa (`.yaml` na pasta `database/`) disponíveis para edição no croqui atual.

#### Scenario: Edição de POI Circular
- **WHEN** o usuário seleciona "Novo Círculo" e define a posição no mapa
- **THEN** o sistema SHALL permitir ajustar o raio e os metadados (ID e Label) do POI circular.

#### Scenario: Edição de POI Retangular (Box)
- **WHEN** o usuário seleciona "Nova Box" e define a posição no mapa
- **THEN** o sistema SHALL permitir ajustar as dimensões, a rotação e os metadados do POI retangular.

#### Scenario: Edição de POI de Área Livre
- **WHEN** o usuário seleciona "Nova Área Livre" e desenha o polígono no mapa
- **THEN** o sistema SHALL permitir ajustar os vértices e os metadados da área livre.

#### Scenario: Persistência de Alterações
- **WHEN** o usuário solicita o salvamento no editor de mapas
- **THEN** o sistema SHALL atualizar o arquivo YAML correspondente preservando comentários e formatação original.
