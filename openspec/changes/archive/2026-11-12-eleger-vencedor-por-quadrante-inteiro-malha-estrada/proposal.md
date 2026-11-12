## Why

Ao comparar as malhas rodoviárias geradas para dois picos vizinhos separados por apenas `3,3 km` (Gruta da Lapinha e Gruta do Baú), observou-se que `41` quadrantes compartilhados (no mesmo anel e mesma coordenada `(ix, iy)`) elegeram nós vencedores distintos, limitando a colisão geral a `84,3%` (`64,7%` no Anel 1, `91,6%` no Anel 2 e `88,9%` no Anel 3). A investigação revelou duas causas determinísticas:
1. **Recorte de quadrantes ao meio antes da votação**: o algoritmo filtrava cada nó individualmente pelos raios de transição (`15 km`, `60 km`, `150 km`) e pelo teto de `200 km` por estrada **antes** de realizar a eleição do vencedor do quadrante `(anel, ix, iy)`. Assim, quando uma fronteira de anel ou o limite de `200 km` cortava um quadrante ao meio, o vencedor oficial do quadrante caía de um lado da linha para um pico e do outro lado para o pico vizinho, fazendo um dos picos eleger um "vice-campeão" local naquele mesmo quadrante.
2. **Interferência de vias locais no grau de cruzamento de rodovias regionais**: o cálculo de `grau_cruzamento` na prioridade intrínseca contava arestas incidentes de qualquer hierarquia (`len(adjacencia[nid])`). Como a BBox 1 (`4 km`) inclui vias `residential`/`service`/`track` (`rank 5..6`) e a BBox 2 (`60 km`) inclui vias `tertiary` (`rank 4`), uma rodovia `tertiary` ou `secondary` que cruzava a fronteira de `4 km` ou `60 km` tinha seu grau inflado por ruelas locais apenas para um dos picos, desempatando para nós diferentes na mesma rodovia.

## What Changes

- **Eleição intrínseca por quadrante inteiro em `gerar_malha_estrada_pico`**:
  - Em cada nível de grade (`Anel 1: 0.02°, rank <= 6`, `Anel 2: 0.06°, rank <= 4`, `Anel 3: 0.18°, rank <= 3`), todos os nós alcançáveis do quadrante `(anel, ix, iy)` com `rank <= rank_max` concorrem integralmente para eleger o vencedor intrínseco oficial daquele quadrante, sem descartar candidatos previamente pelos cortes de `15 km`, `60 km`, `150 km` ou `200 km` por estrada.
  - Todo quadrante `(anel, ix, iy)` que possua ao menos um nó elegível alcançável dentro da faixa radial daquele anel (`<= 15 km`, `15–60 km`, `60–150 km`) e dentro do alcance rodoviário de `200 km` (`DISTANCIA_MAXIMA_ESTRADA_METROS`) é ativado na malha do pico e contribui com o **vencedor intrínseco oficial do quadrante inteiro** (mesmo que o nó vencedor específico esteja ligeiramente além da fronteira radial ou de `200 km` por estrada).
- **Grau de cruzamento estável por camada hierárquica de BBox**:
  - Ao calcular a prioridade intrínseca de um nó de rodovia regional (`rank <= 3`, extraído na BBox de `150 km`), o grau de cruzamento contabiliza apenas vizinhos de `rank <= 3`.
  - Para um nó de rodovia `tertiary` (`rank == 4`, extraído na BBox de `60 km`), o grau de cruzamento contabiliza apenas vizinhos de `rank <= 4`.
  - Para nós de vias locais (`rank >= 5`, extraídos na BBox de `4 km`), o grau contabiliza todos os vizinhos (`rank <= 6`).

## Capabilities

### New Capabilities
- Nenhuma nova capability.

### Modified Capabilities
- `malha-estrada-osm-precomputada`: Atualiza o requisito de amostragem determinística em 3 anéis concêntricos para eleger o vencedor intrínseco por quadrante inteiro (ativado quando o quadrante alcança a faixa do anel dentro de `200 km` por estrada) e estabilizar o grau de cruzamento por camada hierárquica.

## Impact

- **`aresta_db`**:
  - `scripts/gerar_malha_estrada_lib.py` e `scripts/gerar_malha_estrada_lib_test.py`.
  - Regeneração de `database/br_mg_lagoa_santa_gruta_da_lapinha/malha_estrada.yaml`, `database/br_mg_pedro_leopoldo_gruta_do_bau/malha_estrada.yaml` e artefatos compilados em `generated/`.
