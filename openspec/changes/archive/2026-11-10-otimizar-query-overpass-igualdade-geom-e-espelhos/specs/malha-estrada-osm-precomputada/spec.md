## MODIFIED Requirements

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
