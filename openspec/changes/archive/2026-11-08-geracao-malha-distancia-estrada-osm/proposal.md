# Proposal

## Why

O aplicativo móvel (`aresta_app`) e o contrato compartilhado (`aresta_api`) já suportam o cálculo offline de distância rodoviária estimada via KD-Tree 2D a partir das tabelas `catalogo_nos_estrada` e `catalogo_distancias_estrada` do `catalogo.db`. Porém, o pipeline do `aresta_db` ainda não extrai a malha viária do OpenStreetMap (Overpass API), não computa as distâncias por estrada (Dijkstra invertido com amostragem determinística em 3 anéis concêntricos e portais de borda) e ainda não popula nem sincroniza essas tabelas em `gerar_catalogo_sqlite_lib.py`, `gerar_deltas_catalogo.py` e `sincronizar_d1_lib.py`.

## What Changes

- **Atualização do Submódulo `aresta_api`**:
  - Sincronização de `aresta_db/aresta_api` com as tabelas `catalogo_nos_estrada` e `catalogo_distancias_estrada` (`sql/catalogo.sql`) e os schemas `CatalogoNoEstrada` e `CatalogoDistanciaEstrada` (`openapi/catalogo.yaml`).
- **Biblioteca Modular de Extração OSM e Cálculo de Malha Rodoviária (`scripts/gerar_malha_estrada_lib.py`)**:
  - Consulta à Overpass API (com cliente injetável e biblioteca `scripts/cliente_overpass_fake.py` testada 1:1) para extrair o grafo rodoviário num raio de 180 km em torno da coordenada `localizacao` do pico.
  - Filtragem do maior componente conexo para descartar ilhas isoladas no OSM, identificação do nó mais próximo ao estacionamento (`distancia_metros = 0`) e execução de Dijkstra invertido em Python puro (`heapq`) ponderado pelo comprimento geodésico das arestas.
  - Amostragem espacial determinística em 3 anéis concêntricos ancorados em `(0°, 0°)` com grades encaixadas $3 \times 3$ (`0.02°` de 0 a 15 km; `0.06°` de 15 a 60 km; `0.18°` de 60 a 180 km), elegendo o nó vencedor de cada célula pela prioridade intrínseca `(rank_rodovia, -grau_cruzamento, crc32(no_osm_id))` e marcando até 8 portais de borda cardeais/colaterais (`na_borda = 1`).
- **Persistência Incremental e Exportação CSV em `scripts/gerar_catalogo_sqlite_lib.py`**:
  - Criação e validação das tabelas `catalogo_nos_estrada` e `catalogo_distancias_estrada` (e índice `idx_catalogo_distancias_estrada_no`) em `inicializar_banco_catalogo`.
  - Preservação incremental da malha já calculada no `catalogo.db` quando a coordenada de localização do croqui não mudar (evitando chamadas desnecessárias à Overpass API durante recompilações de texto/vias), recalculando apenas quando um croqui com localização válida ainda não possuir malha ou quando for solicitado explicitamente.
  - Remoção em cascata das distâncias do croqui e limpeza de nós órfãos em `catalogo_nos_estrada` que não sejam mais referenciados por nenhum croqui em `catalogo_distancias_estrada`.
  - Inclusão das novas tabelas no cálculo de `versao_catalogo` e na exportação determinística para CSV (`catalogo_nos_estrada.csv` e `catalogo_distancias_estrada.csv`).
- **Cálculo de Deltas e Sincronização com Cloudflare D1 (`scripts/gerar_deltas_catalogo.py` e `serving/sincronizar_d1_lib.py`)**:
  - Extensão de `calcular_deltas_catalogo` e `gerar_payload_d1` para computar `upserts` e `deletes` de `nos_estrada` e `distancias_estrada` via `EXCEPT`.
  - Extensão de `inicializar_schema_d1` e `aplicar_upserts_e_deletes_d1` em `serving/sincronizar_d1_lib.py` para manter as tabelas espelhadas no Cloudflare D1.

## Capabilities

### New Capabilities
- `malha-estrada-osm-precomputada`: Extração do grafo viário do OpenStreetMap via Overpass API, cálculo de caminhos mínimos por Dijkstra invertido a partir do estacionamento do pico, deduplicação determinística em 3 anéis concêntricos ($3 \times 3$) e eleição de portais de borda.

### Modified Capabilities
- `catalogo-sqlite-delta-sync`: Inclusão das tabelas `catalogo_nos_estrada` e `catalogo_distancias_estrada` na geração incremental do `catalogo.db`, no hash `versao_catalogo`, na exportação CSV, no cálculo de deltas SQL (`gerar_deltas_catalogo.py`) e na sincronização com o Cloudflare D1 (`sincronizar_d1_lib.py`).

## Impact

- **Submódulo de Contratos (`aresta_api/`)**:
  - `sql/catalogo.sql`, `openapi/catalogo.yaml` e artefatos gerados em `sql/generated/` e `openapi/generated/`.
- **Scripts de Geração e Compilação (`scripts/`)**:
  - Novos módulos `scripts/gerar_malha_estrada_lib.py` (+ `scripts/gerar_malha_estrada_lib_test.py`) e `scripts/cliente_overpass_fake.py` (+ `scripts/cliente_overpass_fake_test.py`).
  - `scripts/gerar_catalogo_sqlite_lib.py` (+ `scripts/gerar_catalogo_sqlite_lib_test.py`).
  - `scripts/gerar_deltas_catalogo.py` (+ `scripts/gerar_deltas_catalogo_test.py`).
- **Pipeline de Serving (`serving/`)**:
  - `serving/sincronizar_d1_lib.py` (+ `serving/sincronizar_d1_lib_test.py`).
