# Spec Delta

## MODIFIED Requirements

### Requirement: Extração do grafo viário do OpenStreetMap e filtragem do maior componente conexo
O gerador de malha rodoviária SHALL consultar a Overpass API (com cabeçalho `User-Agent` identificável do projeto, negociação de compressão `Accept-Encoding: zstd, br, gzip, deflate` com descompressão em streaming e failover automático entre múltiplos espelhos públicos oficiais da Overpass API) em torno da coordenada do estacionamento do pico utilizando 3 Bounding Boxes `(sul, oeste, norte, leste)` disjuntas com ordenação Quadtile (`out body qt; >; out skel qt;`):
1. **BBox de 4 km**: vias de acesso local (`residential`, `living_street`, `road`, `track`, `service`, `unclassified`);
2. **BBox de 60 km**: vias `tertiary` e `tertiary_link`;
3. **BBox de 180 km**: vias `motorway`, `motorway_link`, `trunk`, `trunk_link`, `primary`, `primary_link`, `secondary` e `secondary_link`.
O gerador SHALL preservar integralmente os nós das `ways` na construção do grafo ponderado por tempo sem trânsito e comprimento geodésico em metros, reportar o progresso por etapa via callback opcional (com suporte a cancelamento cooperativo e chamada a `/api/kill_my_queries` ao cancelar ou sofrer timeout) e reter o maior componente conexo antes de escolher o nó de ancoragem (`no_pico`). No diálogo de progresso do Editor Desktop (`DialogoProgressoMalhaEstrada`), atualizações sucessivas da etapa de recebimento em blocos SHALL atualizar a última linha do log *in-place* em vez de acrescentar novas linhas repetidas.

#### Scenario: Restrição de vias residenciais e locais ao micro-anel de 4 km
- **WHEN** a consulta Overpass é construída para a coordenada de um pico
- **THEN** a query contém exatamente 3 cláusulas de Bounding Box `(sul,oeste,norte,leste)` sem sobreposição de tipos de `highway` (`4 km` para locais + `unclassified`, `60 km` para `tertiary|tertiary_link` e `180 km` para `motorway..secondary_link`) e finaliza com `out body qt; >; out skel qt;`.

#### Scenario: Descompressão em streaming para respostas zstd, br, gzip, deflate ou identity
- **WHEN** o servidor Overpass responde com `Content-Encoding` igual a `zstd`, `br`, `gzip`, `deflate` ou sem compressão
- **THEN** o cliente descomprime os blocos de 64 KB em streaming, reporta os megabytes trafegados na rede e reconstrói os elementos JSON integralmente.

#### Scenario: Notificação de progresso e interrupção por cancelamento cooperativo
- **WHEN** o gerador é invocado com callbacks de progresso e verificação de cancelamento e o usuário solicita o cancelamento durante uma das etapas ou durante o streaming (ou um espelho sofre timeout de leitura)
- **THEN** o gerador emite os eventos de progresso das etapas concluídas, dispara em best-effort `/api/kill_my_queries` no espelho ativo para liberar o slot do IP e interrompe imediatamente o processamento levantando `ErroMalhaEstradaCancelada` (no cancelamento) ou avançando para o próximo espelho (no timeout).

#### Scenario: Atualização in-place da linha de download no log do DialogoProgressoMalhaEstrada
- **WHEN** múltiplos eventos consecutivos de progresso de download (`"Recebendo malha viária de ..."`) são recebidos pelo `DialogoProgressoMalhaEstrada`
- **THEN** o diálogo substitui a última linha correspondente no histórico textual em vez de empilhar uma linha nova para cada bloco de 64 KB.

#### Scenario: Descarte de ilhas rodoviárias isoladas próximas ao estacionamento
- **WHEN** a resposta do OpenStreetMap contém um pequeno trecho de estrada isolado muito próximo da coordenada do pico e a malha rodoviária principal conectada um pouco mais adiante
- **THEN** o algoritmo descarta o componente isolado, seleciona como `no_pico` o nó mais próximo pertencente ao componente principal e registra `no_pico` com `distancia_metros = 0`.

#### Scenario: Failover automático entre espelhos da Overpass API
- **WHEN** o primeiro espelho público da Overpass API retorna falha de rede, timeout ou HTTP 429/502/504
- **THEN** o cliente tenta automaticamente os espelhos públicos subsequentes configurados até obter resposta válida ou esgotar a lista.

#### Scenario: Pico sem coordenada válida ou grafo vazio
- **WHEN** o croqui não possui coordenada de localização válida (`(0, 0)` ou ausente) ou a consulta não retorna nós conectados
- **THEN** o gerador retorna listas vazias de nós e distâncias sem levantar erro fatal no pipeline.

### Requirement: Persistência pré-computada da malha rodoviária no modelo do Pico
O modelo `Pico` no Protobuf (`croqui.proto`) SHALL declarar `ArquivoMalhaEstrada malha_estrada = 15` (`oneof arquivo { string caminho = 1; MalhaEstradaPico conteudo = 2; }`), persistindo no arquivo fonte `database/<id>/croqui.yaml` apenas a referência `malha_estrada: { caminho: malha_estrada.yaml }` (ou `malha_estrada_<id>.yaml` quando houver múltiplos picos), gravando o conteúdo (`latitude_referencia_e7`, `longitude_referencia_e7` e `nos`) no arquivo YAML dedicado com cabeçalho SPDX ODbL-1.0 e expandindo `malha_estrada.conteudo` ao compilar o `compilado.binarypb`. Uma malha pré-computada SHALL ser considerada atualizada somente quando possuir ao menos um nó, coordenadas de referência idênticas a `pico.localizacao` e todos os nós com `distancia_metros > 0` possuírem `duracao_minutos > 0`.

#### Scenario: Serialização separada em malha_estrada.yaml e linkagem no croqui.yaml
- **WHEN** um croqui possui `pico.malha_estrada.conteudo` preenchido com pontos rodoviários e é salvo pelo Editor ou processado pelo pipeline
- **THEN** `database/<id>/croqui.yaml` armazena apenas `malha_estrada: { caminho: malha_estrada.yaml }` e os pontos são gravados em `database/<id>/malha_estrada.yaml` com cabeçalho SPDX ODbL-1.0.

#### Scenario: Hidratação em memória ao abrir no Editor e expansão no compilado.binarypb
- **WHEN** o Editor carrega `database/<id>/croqui.yaml` ou `compilar_croqui` gera `compilado.binarypb`
- **THEN** o arquivo referenciado em `malha_estrada.caminho` é lido do disco e hidratado em `pico.malha_estrada.conteudo`.

#### Scenario: Validação de sincronia entre a malha pré-computada e a localização atual do pico
- **WHEN** `pico.malha_estrada.conteudo` possui ao menos um nó, todos os nós com `distancia_metros > 0` possuem `duracao_minutos > 0`, e `latitude_referencia_e7 == pico.localizacao.latitude` e `longitude_referencia_e7 == pico.localizacao.longitude`
- **THEN** o sistema considera a malha rodoviária válida e atualizada para a localização atual do pico.

#### Scenario: Detecção de malha defasada após alteração de coordenada do pico
- **WHEN** a coordenada `pico.localizacao` é alterada para um novo par `(latitude, longitude)` diferente de `(latitude_referencia_e7, longitude_referencia_e7)` ou existe algum nó com `distancia_metros > 0` cujo `duracao_minutos <= 0`
- **THEN** o sistema identifica que a malha pré-computada está desatualizada (exibindo alerta no card de localização do pico, no Painel de Qualidade e no deploy).
