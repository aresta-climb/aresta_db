# poi-geometrias-avancadas Specification

## Purpose
Avançar a expressividade e compatibilidade das demarcações no mapa.

## Requirements

### Requirement: Geometrias Avançadas para POIs
O sistema SHALL suportar a declaração e o processamento de pontos de interesse (POIs) com geometrias padronizadas nos arquivos JSON de mapas, usando os tipos estritos `circulo` (substituindo `circular`), `retangulo` (substituindo `box`), `quadrado` (novo formato: x, y, lado) e `poligono` (substituindo `area_livre`). A extração automática de POIs MUST respeitar a ordem de prioridade Círculo > Quadrado > Retângulo.

#### Scenario: Leitura de Quadrado
- **WHEN** o JSON do mapa contém um POI do tipo `quadrado` com os parâmetros `x`, `y` e `lado`
- **THEN** o sistema SHALL processar corretamente este POI respeitando suas dimensões uniformes

#### Scenario: Leitura de Polígono
- **WHEN** o JSON do mapa contém um POI do tipo `poligono` composto por uma lista de coordenadas
- **THEN** o sistema SHALL processar este POI como uma área irregular multivertice
