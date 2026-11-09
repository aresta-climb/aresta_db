# malha-estrada-osm-precomputada Specification

## Purpose
Define o contrato de extração da malha rodoviária do OpenStreetMap via Overpass API, cálculo de caminhos mínimos por Dijkstra invertido a partir do estacionamento do pico, deduplicação determinística em 3 anéis concêntricos e marcação de portais de borda para compor o catálogo SQLite offline.

## Requirements

### Requirement: Extração do grafo viário do OpenStreetMap e filtragem do maior componente conexo
O gerador de malha rodoviária SHALL consultar a Overpass API (com cabeçalho `User-Agent` identificável do projeto e failover automático entre múltiplos espelhos públicos oficiais da Overpass API) em torno da coordenada do estacionamento do pico restringindo vias de acesso local (`residential`, `living_street`, `service`, `track`) a um micro-anel de 4 km ao redor do pico e mantendo o Anel 1 (`15 km`) de `unclassified` a `motorway`, construir um grafo ponderado pelo comprimento geodésico em metros, reportar o progresso por etapa via callback opcional (com suporte a cancelamento cooperativo) e reter o componente conexo ancorado antes de escolher o nó de ancoragem (`no_pico`).

#### Scenario: Restrição de vias residenciais e locais ao micro-anel de 4 km
- **WHEN** a consulta Overpass é construída para a coordenada de um pico próximo a áreas urbanas
- **THEN** a cláusula de vias locais (`residential|living_street|service|track`) utiliza `around:4000` (4 km) enquanto o Anel 1 de `around:15000` (15 km) busca apenas vias de `unclassified` até `motorway`.

#### Scenario: Descarte de ilhas rodoviárias isoladas próximas ao estacionamento
- **WHEN** a resposta do OpenStreetMap contém um pequeno trecho de estrada isolado muito próximo da coordenada do pico e a malha rodoviária principal conectada um pouco mais adiante
- **THEN** o algoritmo descarta o componente isolado, seleciona como `no_pico` o nó mais próximo pertencente ao componente principal e registra `no_pico` com `distancia_metros = 0`.

#### Scenario: Failover automático entre espelhos da Overpass API
- **WHEN** o primeiro espelho público da Overpass API retorna falha de rede, timeout ou HTTP 429/504
- **THEN** o cliente tenta automaticamente os espelhos públicos subsequentes configurados até obter resposta válida ou esgotar a lista.

#### Scenario: Notificação de progresso e interrupção por cancelamento cooperativo
- **WHEN** o gerador é invocado com callbacks de progresso e verificação de cancelamento e o usuário solicita o cancelamento durante uma das etapas
- **THEN** o gerador emite os eventos de progresso das etapas concluídas e interrompe imediatamente o processamento levantando exceção de operação cancelada.

#### Scenario: Pico sem coordenada válida ou grafo vazio
- **WHEN** o croqui não possui coordenada de localização válida (`(0, 0)` ou ausente) ou a consulta não retorna nós conectados
- **THEN** o gerador retorna listas vazias de nós e distâncias sem levantar erro fatal no pipeline.

### Requirement: Cálculo de distâncias por Dijkstra invertido e amostragem determinística em 3 anéis concêntricos
A partir do `no_pico`, o sistema SHALL executar o algoritmo de Dijkstra sobre o grafo viário e amostrar no máximo um nó vencedor por célula de grade global ancorada em `(0°, 0°)` nos 3 anéis concêntricos (`0.02°` de 0 a 15 km; `0.06°` de 15 a 60 km; `0.18°` de 60 a 180 km), elegendo o vencedor pela tupla intrínseca `(rank_rodovia, -grau_cruzamento, crc32(no_osm_id))`.

#### Scenario: Coincidência determinística de nó vencedor entre picos distintos e anéis sobrepostos
- **WHEN** dois picos distintos amostram uma mesma região geográfica (inclusive quando cai no Anel 2 de `0.06°` de um pico e no bloco $3 \times 3$ de `0.18°` do Anel 3 de outro pico)
- **THEN** a função de prioridade intrínseca elege exatamente o mesmo `no_osm_id`, maximizando o compartilhamento de nós na tabela `catalogo_nos_estrada`.

#### Scenario: Cálculo exato da distância rodoviária acumulada até o estacionamento
- **WHEN** um caminho rodoviário no grafo requer contornar uma serra por múltiplos segmentos totalizando 42 km apesar de estar a 14 km em linha reta
- **THEN** `distancia_metros` registrada para o nó amostrado reflete a soma dos comprimentos dos segmentos do caminho mínimo (~42000 m).

### Requirement: Eleição de portais de borda nos octantes externos da malha
O gerador SHALL identificar até 8 portais de borda (`na_borda = 1`), correspondendo a um nó rodoviário principal na faixa externa da malha para cada um dos 8 octantes direcionais (N, NE, L, SE, S, SO, O, NO) em torno do pico.

#### Scenario: Marcação de portais de borda por octante direcional
- **WHEN** a malha de um pico possui nós alcançáveis distribuídos em diferentes direções cardeais e colaterais no anel externo
- **THEN** o sistema marca `na_borda = 1` para o nó representante de cada octante ocupado (até 8 portais) e `na_borda = 0` para os demais nós.

### Requirement: Persistência pré-computada da malha rodoviária no modelo do Pico
O modelo `Pico` no Protobuf (`croqui.proto`) SHALL declarar `ArquivoMalhaEstrada malha_estrada = 15` (`oneof arquivo { string caminho = 1; MalhaEstradaPico conteudo = 2; }`), persistindo no arquivo fonte `database/<id>/croqui.yaml` apenas a referência `malha_estrada: { caminho: malha_estrada.yaml }` (ou `malha_estrada_<id>.yaml` quando houver múltiplos picos), gravando o conteúdo (`latitude_referencia_e7`, `longitude_referencia_e7` e `pontos`) no arquivo YAML dedicado com cabeçalho SPDX ODbL-1.0 e expandindo `malha_estrada.conteudo` ao compilar o `compilado.binarypb`.

#### Scenario: Serialização separada em malha_estrada.yaml e linkagem no croqui.yaml
- **WHEN** um croqui possui `pico.malha_estrada.conteudo` preenchido com pontos rodoviários e é salvo pelo Editor ou processado pelo pipeline
- **THEN** `database/<id>/croqui.yaml` armazena apenas `malha_estrada: { caminho: malha_estrada.yaml }` e os pontos são gravados em `database/<id>/malha_estrada.yaml` com cabeçalho SPDX ODbL-1.0.

#### Scenario: Hidratação em memória ao abrir no Editor e expansão no compilado.binarypb
- **WHEN** o Editor carrega `database/<id>/croqui.yaml` ou `compilar_croqui` gera `compilado.binarypb`
- **THEN** o arquivo referenciado em `malha_estrada.caminho` é lido do disco e hidratado em `pico.malha_estrada.conteudo`.

#### Scenario: Validação de sincronia entre a malha pré-computada e a localização atual do pico
- **WHEN** `pico.malha_estrada.conteudo` possui ao menos um nó e `latitude_referencia_e7 == pico.localizacao.latitude` e `longitude_referencia_e7 == pico.localizacao.longitude`
- **THEN** o sistema considera a malha rodoviária válida e atualizada para a localização atual do pico.

#### Scenario: Detecção de malha defasada após alteração de coordenada do pico
- **WHEN** a coordenada `pico.localizacao` é alterada para um novo par `(latitude, longitude)` diferente de `(latitude_referencia_e7, longitude_referencia_e7)`
- **THEN** o sistema identifica que a malha pré-computada está desatualizada para a nova localização.
