# malha-estrada-osm-precomputada Specification

## Purpose
Define o contrato de extração da malha rodoviária do OpenStreetMap via Overpass API, cálculo de caminhos mínimos por Dijkstra invertido a partir do estacionamento do pico, deduplicação determinística em 3 anéis concêntricos e marcação de portais de borda para compor o catálogo SQLite offline.

## Requirements

### Requirement: Extração do grafo viário do OpenStreetMap e filtragem do maior componente conexo
O gerador de malha rodoviária SHALL consultar a Overpass API (com cabeçalho `User-Agent` identificável do projeto, negociação de compressão `Accept-Encoding: zstd, br, gzip, deflate` com descompressão em streaming e failover automático entre múltiplos espelhos diretos da Overpass API na ordem `lz4.overpass-api.de`, `z.overpass-api.de` e `overpass.private.coffee`, com timeout padrão de `60s` por tentativa) em torno da coordenada do estacionamento do pico utilizando 3 Bounding Boxes `(sul, oeste, norte, leste)` disjuntas com consultas por igualdade exata de tag (`way["highway"="<tipo>"](bbox);`) nas caixas regionais e saída `out geom qt;` (sem recurse down `>;`):
1. **BBox de 4 km**: vias de acesso local (`residential`, `living_street`, `road`, `track`, `service`, `unclassified`);
2. **BBox de 60 km**: vias `tertiary` e `tertiary_link` consultadas por igualdade exata (`["highway"="..."]`);
3. **BBox de 150 km**: vias `motorway`, `motorway_link`, `trunk`, `trunk_link`, `primary`, `primary_link`, `secondary` e `secondary_link` consultadas por igualdade exata (`["highway"="..."]`).
O gerador SHALL extrair as coordenadas `(lat, lon)` pareadas de `nodes` e `geometry` de cada `way` (além de elementos `node` explícitos quando presentes), preservar integralmente os nós das `ways` na construção do grafo ponderado por tempo sem trânsito e comprimento geodésico em metros, reportar o progresso por etapa via callback opcional (incluindo aviso explícito quando um espelho falha e aciona failover, com suporte a cancelamento cooperativo e chamada a `/api/kill_my_queries` ao cancelar ou sofrer timeout) e reter o maior componente conexo antes de escolher o nó de ancoragem (`no_pico`). No diálogo de progresso do Editor Desktop (`DialogoProgressoMalhaEstrada`), cada linha do log SHALL exibir o timestamp e o tempo decorrido desde o início da operação (`[HH:MM:SS +X.Xs] [XX%] ...`), e atualizações sucessivas da etapa de recebimento em blocos SHALL atualizar a última linha do log *in-place*.

#### Scenario: Restrição de vias residenciais e locais ao micro-anel de 4 km
- **WHEN** a consulta Overpass é construída para a coordenada de um pico
- **THEN** a query declara `[out:json][timeout:60];`, utiliza as 3 Bounding Boxes `(sul,oeste,norte,leste)` sem sobreposição de tipos de `highway` (`4 km` para locais + `unclassified`, `60 km` com igualdade exata para `tertiary` e `tertiary_link`, e `150 km` com igualdade exata para `motorway..secondary_link`) e finaliza com `out geom qt;`.

#### Scenario: Descompressão em streaming para respostas zstd, br, gzip, deflate ou identity
- **WHEN** o servidor Overpass responde com `Content-Encoding` igual a `zstd`, `br`, `gzip`, `deflate` ou sem compressão
- **THEN** o cliente descomprime os blocos de 64 KB em streaming, reporta os megabytes trafegados na rede e reconstrói os elementos JSON integralmente.

#### Scenario: Notificação de progresso e interrupção por cancelamento cooperativo
- **WHEN** o gerador é invocado com callbacks de progresso e verificação de cancelamento e o usuário solicita o cancelamento durante uma das etapas ou durante o streaming (ou um espelho sofre timeout de leitura)
- **THEN** o gerador emite os eventos de progresso das etapas concluídas, dispara em best-effort `/api/kill_my_queries` no espelho ativo para liberar o slot do IP e interrompe imediatamente o processamento levantando `ErroMalhaEstradaCancelada` (no cancelamento) ou avançando para o próximo espelho (no timeout).

#### Scenario: Atualização in-place da linha de download no log do DialogoProgressoMalhaEstrada
- **WHEN** múltiplos eventos consecutivos de progresso de download (`"Recebendo malha viária de ..."`) são recebidos pelo `DialogoProgressoMalhaEstrada`
- **THEN** o diálogo formata cada linha com o timestamp e o tempo decorrido (`[HH:MM:SS +X.Xs] [XX%] ...`) e substitui a última linha de recebimento *in-place* em vez de empilhar uma linha nova para cada bloco de 64 KB.

#### Scenario: Descarte de ilhas rodoviárias isoladas próximas ao estacionamento
- **WHEN** a resposta do OpenStreetMap contém um pequeno trecho de estrada isolado muito próximo da coordenada do pico e a malha rodoviária principal conectada um pouco mais adiante
- **THEN** o algoritmo descarta o componente isolado, seleciona como `no_pico` o nó mais próximo pertencente ao componente principal e registra `no_pico` com `distancia_metros = 0`.

#### Scenario: Failover automático entre espelhos da Overpass API
- **WHEN** o primeiro espelho público da Overpass API retorna falha de rede, timeout ou HTTP 429/502/504
- **THEN** o cliente emite notificação de progresso relatando a falha no espelho atual e tenta automaticamente os espelhos públicos subsequentes configurados até obter resposta válida ou esgotar a lista.

#### Scenario: Pico sem coordenada válida ou grafo vazio
- **WHEN** o croqui não possui coordenada de localização válida (`(0, 0)` ou ausente) ou a consulta não retorna nós conectados
- **THEN** o gerador retorna listas vazias de nós e distâncias sem levantar erro fatal no pipeline.

### Requirement: Cálculo de distâncias por Dijkstra invertido e amostragem determinística em 3 anéis concêntricos
A partir do `no_pico`, o sistema SHALL executar o algoritmo de Dijkstra sobre o grafo viário e amostrar os quadrantes de grade global ancorada em `(0°, 0°)` nos 3 anéis concêntricos (`0.02°` com `rank <= 6` de 0 a 15 km; `0.06°` com `rank <= 4` de 15 a 60 km; `0.18°` com `rank <= 3` de 60 a 150 km em linha reta). Em cada anel, todos os nós alcançáveis pertencentes ao quadrante `(anel, ix, iy)` com `rank_rodovia <= rank_max` SHALL concorrer integralmente (sem recorte prévio do quadrante pelas fronteiras de `15 km`, `60 km`, `150 km` ou `200 km`) para eleger o vencedor intrínseco oficial do quadrante pela tupla `(rank_rodovia, -grau_cruzamento_estavel, crc32(no_osm_id))`, onde `grau_cruzamento_estavel` contabiliza apenas vizinhos compatíveis com a camada da BBox do nó (`rank <= 3` para nós com `rank <= 3`; `rank <= 4` para nós com `rank == 4`; `rank <= 6` para nós com `rank >= 5`). Um quadrante `(anel, ix, iy)` SHALL ser ativado e incluir seu vencedor intrínseco oficial na malha sempre que possuir ao menos um nó elegível na faixa radial do respectivo anel com distância rodoviária acumulada até `200.000 metros` (`200 km` por estrada), descartando quadrantes cujos nós na faixa radial excedam todos `200.000 metros` por estrada.

#### Scenario: Coincidência determinística de nó vencedor entre picos distintos e anéis sobrepostos
- **WHEN** dois picos distintos ativam um mesmo quadrante `(anel, ix, iy)` (inclusive quando o quadrante é cortado pela fronteira de `15 km`, `60 km`, `150 km` ou `200 km` por estrada, ou quando um dos picos inclui vias locais de BBox menor que interceptam a rodovia principal)
- **THEN** a eleição por quadrante inteiro com grau de cruzamento estável elege exatamente o mesmo `no_osm_id` oficial do quadrante para ambos os picos, maximizando o compartilhamento de nós na tabela `catalogo_nos_estrada`.

#### Scenario: Cálculo exato da distância rodoviária acumulada até o estacionamento
- **WHEN** um caminho rodoviário no grafo requer contornar uma serra por múltiplos segmentos totalizando 42 km apesar de estar a 14 km em linha reta
- **THEN** `distancia_metros` registrada para o nó amostrado reflete a soma dos comprimentos dos segmentos do caminho mínimo (~42000 m), e qualquer quadrante cujos nós elegíveis excedam todos `200.000 m` por estrada é excluído da amostragem.

### Requirement: Eleição de portais de borda nos octantes externos da malha
O gerador SHALL identificar até 8 portais de borda (`na_borda = 1`), correspondendo a um nó rodoviário principal na faixa externa da malha para cada um dos 8 octantes direcionais (N, NE, L, SE, S, SO, O, NO) em torno do pico.

#### Scenario: Marcação de portais de borda por octante direcional
- **WHEN** a malha de um pico possui nós alcançáveis distribuídos em diferentes direções cardeais e colaterais no anel externo
- **THEN** o sistema marca `na_borda = 1` para o nó representante de cada octante ocupado (até 8 portais) e `na_borda = 0` para os demais nós.

### Requirement: Persistência pré-computada da malha rodoviária no modelo do Pico
O modelo `Pico` no Protobuf (`croqui.proto`) SHALL declarar `ArquivoMalhaEstrada malha_estrada = 15` (`oneof arquivo { string caminho = 1; MalhaEstradaPico conteudo = 2; }`), onde `MalhaEstradaPico` inclui `int32 versao = 4` (gravado com `VERSAO_ATUAL_MALHA_ESTRADA = 2`), persistindo no arquivo fonte `database/<id>/croqui.yaml` apenas a referência `malha_estrada: { caminho: malha_estrada.yaml }` (ou `malha_estrada_<id>.yaml` quando houver múltiplos picos), gravando o conteúdo (`latitude_referencia_e7`, `longitude_referencia_e7`, `versao` e `nos`) no arquivo YAML dedicado com cabeçalho SPDX ODbL-1.0 e expandindo `malha_estrada.conteudo` ao compilar o `compilado.binarypb`. Uma malha pré-computada SHALL ser considerada sincronizada (apta a exportar pontos para o catálogo SQLite) quando possuir ao menos um nó, coordenadas de referência idênticas a `pico.localizacao` e todos os nós com `distancia_metros > 0` possuírem `duracao_minutos > 0`, e SHALL ser considerada integralmente atualizada somente quando adicionalmente `versao >= VERSAO_ATUAL_MALHA_ESTRADA` (`2`).

#### Scenario: Serialização separada em malha_estrada.yaml e linkagem no croqui.yaml
- **WHEN** um croqui possui `pico.malha_estrada.conteudo` preenchido com pontos rodoviários e é salvo pelo Editor ou processado pelo pipeline
- **THEN** `database/<id>/croqui.yaml` armazena apenas `malha_estrada: { caminho: malha_estrada.yaml }` e os pontos (junto com `versao: 2`) são gravados em `database/<id>/malha_estrada.yaml` com cabeçalho SPDX ODbL-1.0.

#### Scenario: Hidratação em memória ao abrir no Editor e expansão no compilado.binarypb
- **WHEN** o Editor carrega `database/<id>/croqui.yaml` ou `compilar_croqui` gera `compilado.binarypb`
- **THEN** o arquivo referenciado em `malha_estrada.caminho` é lido do disco e hidratado em `pico.malha_estrada.conteudo`.

#### Scenario: Validação de sincronia entre a malha pré-computada e a localização atual do pico
- **WHEN** `pico.malha_estrada.conteudo` possui ao menos um nó, todos os nós com `distancia_metros > 0` possuem `duracao_minutos > 0`, `latitude_referencia_e7 == pico.localizacao.latitude`, `longitude_referencia_e7 == pico.localizacao.longitude` e `versao >= 2`
- **THEN** o sistema considera a malha rodoviária válida e integralmente atualizada para a localização atual do pico.

#### Scenario: Detecção de malha defasada após alteração de coordenada do pico
- **WHEN** a coordenada `pico.localizacao` é alterada para um novo par `(latitude, longitude)` diferente de `(latitude_referencia_e7, longitude_referencia_e7)`, ou existe algum nó com `distancia_metros > 0` cujo `duracao_minutos <= 0`, ou `versao < 2`
- **THEN** o sistema identifica que a malha pré-computada está desatualizada (exibindo alerta específico de versão ou ausência no card de localização do pico, no Painel de Qualidade e no deploy, mas mantendo a exportação para o catálogo caso a coordenada e `duracao_minutos` sejam válidos).
