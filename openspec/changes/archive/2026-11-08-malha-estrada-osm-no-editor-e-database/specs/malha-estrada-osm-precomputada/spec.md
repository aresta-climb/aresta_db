# Spec Delta

## MODIFIED Requirements

### Requirement: Extração do grafo viário do OpenStreetMap e filtragem do maior componente conexo
O gerador de malha rodoviária SHALL consultar a Overpass API (com cabeçalho `User-Agent` identificável do projeto e failover automático entre múltiplos espelhos públicos oficiais da Overpass API) em torno da coordenada do estacionamento do pico, construir um grafo ponderado pelo comprimento geodésico em metros e reter o componente conexo ancorado antes de escolher o nó de ancoragem (`no_pico`).

#### Scenario: Descarte de ilhas rodoviárias isoladas próximas ao estacionamento
- **WHEN** a resposta do OpenStreetMap contém um pequeno trecho de estrada isolado muito próximo da coordenada do pico e a malha rodoviária principal conectada um pouco mais adiante
- **THEN** o algoritmo descarta o componente isolado, seleciona como `no_pico` o nó mais próximo pertencente ao componente principal e registra `no_pico` com `distancia_metros = 0`.

#### Scenario: Failover automático entre espelhos da Overpass API
- **WHEN** o primeiro espelho público da Overpass API retorna falha de rede, timeout ou HTTP 429/504
- **THEN** o cliente tenta automaticamente os espelhos públicos subsequentes configurados até obter resposta válida ou esgotar a lista.

#### Scenario: Pico sem coordenada válida ou grafo vazio
- **WHEN** o croqui não possui coordenada de localização válida (`(0, 0)` ou ausente) ou a consulta não retorna nós conectados
- **THEN** o gerador retorna listas vazias de nós e distâncias sem levantar erro fatal no pipeline.

## ADDED Requirements

### Requirement: Persistência pré-computada da malha rodoviária no modelo do Pico
O modelo `Pico` no Protobuf (`croqui.proto`) e no arquivo fonte `database/<id>/croqui.yaml` SHALL armazenar a malha rodoviária pré-computada em `malha_estrada`, contendo a coordenada de referência (`latitude_referencia_e7` e `longitude_referencia_e7`) para a qual os pontos foram calculados e a lista ordenada de nós (`no_osm_id`, `latitude_e7`, `longitude_e7`, `distancia_metros` e `na_borda`).

#### Scenario: Validação de sincronia entre a malha pré-computada e a localização atual do pico
- **WHEN** `pico.malha_estrada` possui ao menos um nó e `latitude_referencia_e7 == pico.localizacao.latitude` e `longitude_referencia_e7 == pico.localizacao.longitude`
- **THEN** o sistema considera a malha rodoviária válida e atualizada para a localização atual do pico.

#### Scenario: Detecção de malha defasada após alteração de coordenada do pico
- **WHEN** a coordenada `pico.localizacao` é alterada para um novo par `(latitude, longitude)` diferente de `(latitude_referencia_e7, longitude_referencia_e7)`
- **THEN** o sistema identifica que a malha pré-computada está desatualizada para a nova localização.
