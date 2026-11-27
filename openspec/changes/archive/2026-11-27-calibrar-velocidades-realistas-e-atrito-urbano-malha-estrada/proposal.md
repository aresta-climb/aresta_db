## Why

Os tempos de viagem gerados pela malha rodoviária offline estavam ~25% otimistas em relação ao tempo médio real (ex.: ~45–50 min de Belo Horizonte até a Gruta do Baú e a Gruta da Lapinha, quando em fluxo normal levam ~1h00–1h05 e ~1h05–1h10). Isso ocorria porque a estimativa usava `0.85 × maxspeed` ou velocidades altas (`70–80 km/h`) em arteriais urbanas (`trunk`/`primary`), ignorava tags de perímetro urbano (`lit=yes`), assumia asfalto rápido em vicinais `unclassified` sem tag `surface` e não aplicava nenhum atraso em cruzamentos ou rotatórias.

## What Changes

- **Calibração realista de velocidades por segmento (`calcular_velocidade_sem_transito_kmh`)**:
  - Diferenciação explícita entre terra e asfalto: `highway=track` a `15 km/h`; `surface` não pavimentada ou `tracktype=grade2..5` a `24 km/h` (vias principais) ou `18 km/h` (locais); `highway=unclassified` sem `surface` pavimentada e sem `lit=yes` tratada como vicinal rural (`22 km/h`).
  - Detecção de contexto urbano (`lit=yes`, `maxspeed <= 60` ou vias `residential`/`living_street`/`service`/`road`): placa limitada a `60 km/h` e velocidade média efetiva de `0.62 × limite` (respeitando tetos urbanos por classe) para refletir semáforos, lombadas e radares.
  - Rotatórias (`junction=roundabout` ou `circular`) limitadas a `25 km/h`.
  - Rodovias intermunicipais pavimentadas calibradas com tetos efetivos (`motorway=82`, `trunk=68`, `primary=58`, `secondary=46`, `tertiary=36`, `unclassified=30 km/h`) e `0.74 × maxspeed`.
- **Penalidade de interseção no grafo (`_extrair_grafo_maior_componente`)**:
  - Arestas incidentes a nós de cruzamento (`grau >= 3`) recebem penalidade de atraso (`+2,0s` por extremidade em `rank >= 2` e `+1,0s` em `rank == 1`), penalizando travessias urbanas cheias de esquinas.
- **Versionamento da malha (`VERSAO_ATUAL_MALHA_ESTRADA = 3`)** e regeneração de Gruta da Lapinha e Gruta do Baú.

## Capabilities

### New Capabilities
- Nenhuma nova capability.

### Modified Capabilities
- `malha-estrada-osm-precomputada`: Atualiza a ponderação de tempo do grafo viário com velocidades médias efetivas urbanas/rurais, penalidade de cruzamentos e versão `3` da malha pré-computada.

## Impact

- **`aresta_db`**:
  - `scripts/gerar_malha_estrada_lib.py` e `scripts/gerar_malha_estrada_lib_test.py`.
  - `editor/views/widget_mensagem_coordenada_test.py` (se aplicável à versão `3`).
  - Regeneração de `database/br_mg_lagoa_santa_gruta_da_lapinha/malha_estrada.yaml`, `database/br_mg_pedro_leopoldo_gruta_do_bau/malha_estrada.yaml` e artefatos em `generated/`.
