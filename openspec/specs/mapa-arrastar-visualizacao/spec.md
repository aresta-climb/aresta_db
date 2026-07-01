# mapa-arrastar-visualizacao Specification

## Requirements
### Requirement: Arrasto da Visualização do Mapa
O sistema SHALL permitir que o usuário arraste (pan) a área visível do mapa clicando e segurando no fundo da imagem e movendo o mouse, melhorando a experiência de navegação em áreas extensas de mapas ou quando o zoom está aproximado.

#### Scenario: Arrasto do fundo sem interagir com POI
- **WHEN** o usuário clica em uma área do mapa que não contém um POI e arrasta o cursor
- **THEN** o sistema SHALL mover a visualização do mapa acompanhando o movimento do cursor

#### Scenario: Prioridade do POI sobre o arrasto
- **WHEN** o usuário clica sobre um POI e arrasta o cursor
- **THEN** o sistema SHALL mover o POI selecionado e NÃO SHALL mover a visualização do mapa

#### Scenario: Indicação visual do cursor
- **WHEN** o mouse está sobre a área de fundo do mapa, sem clicar em nada e sem estar sobre um POI
- **THEN** o sistema SHALL exibir um cursor indicativo de que a área pode ser arrastada (ex: mão aberta)
