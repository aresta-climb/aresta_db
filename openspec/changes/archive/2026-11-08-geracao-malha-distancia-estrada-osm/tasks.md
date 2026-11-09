# Tasks

## 1. Sincronização do Submódulo `aresta_api` no `aresta_db`

- [x] 1.1 Sincronizar os contratos SQL e OpenAPI (`sql/catalogo.sql`, `openapi/catalogo.yaml`, `src/validador_paridade.py` e testes) em `aresta_db/aresta_api`, executar `python build.py -f` e verificar que `pytest` dentro de `aresta_db/aresta_api` passa com 100% de cobertura

## 2. Biblioteca de Extração OSM, Dijkstra Invertido e Amostragem 3 Anéis (`scripts/gerar_malha_estrada_lib.py`)

- [x] 2.1 Criar os testes espelhados `scripts/cliente_overpass_fake_test.py` e `scripts/gerar_malha_estrada_lib_test.py` cobrindo: cliente Fake da Overpass API (respostas pré-configuradas e simulação de erro), filtragem do maior componente conexo descartando ilhas isoladas, inclusão do nó do estacionamento (`distancia_metros = 0`), Dijkstra invertido ponderado por Haversine, deduplicação determinística nos 3 anéis concêntricos (`0.02°`, `0.06°`, `0.18°`) pela tupla `(rank_rodovia, -grau_cruzamento, crc32(no_osm_id))` e marcação de até 8 portais de borda (`na_borda = 1`), verificando a falha inicial (Red) via `pytest`
- [x] 2.2 Implementar `scripts/cliente_overpass_fake.py` e `scripts/gerar_malha_estrada_lib.py` em Python puro (com tipagem estrita `mypy --strict`) e verificar que `pytest scripts/cliente_overpass_fake_test.py scripts/gerar_malha_estrada_lib_test.py --cov` passa com 100% de cobertura

## 3. Persistência Incremental da Malha no `catalogo.db` (`scripts/gerar_catalogo_sqlite_lib.py`)

- [x] 3.1 Adicionar testes comportamentais em `scripts/gerar_catalogo_sqlite_lib_test.py` validando: criação das tabelas `catalogo_nos_estrada` e `catalogo_distancias_estrada`, inserção/atualização da malha rodoviária quando `cliente_overpass` é fornecido, preservação da malha existente quando apenas metadados do croqui mudam, limpeza em cascata de `catalogo_distancias_estrada` e nós órfãos de `catalogo_nos_estrada` quando um croqui é removido/despublicado, e inclusão da malha no cálculo de `versao_catalogo`, verificando a falha inicial (Red) via `pytest`
- [x] 3.2 Atualizar `scripts/gerar_catalogo_sqlite_lib.py` para suportar as tabelas `catalogo_nos_estrada` e `catalogo_distancias_estrada` (incluindo limpeza de nós órfãos, `calcular_versao_catalogo` e integração opcional com `cliente_overpass`) e verificar que `pytest scripts/gerar_catalogo_sqlite_lib_test.py --cov` passa com 100% de cobertura

## 4. Cálculo de Deltas e Sincronização com Cloudflare D1 (`scripts/gerar_deltas_catalogo.py` e `serving/sincronizar_d1_lib.py`)

- [x] 4.1 Adicionar testes em `scripts/gerar_deltas_catalogo_test.py` e `serving/sincronizar_d1_lib_test.py` validando a extração de `upserts` e `deletes` de `nos_estrada` e `distancias_estrada` via `EXCEPT` e a aplicação em lotes nas tabelas espelho do Cloudflare D1, verificando a falha inicial (Red) via `pytest`
- [x] 4.2 Atualizar `scripts/gerar_deltas_catalogo.py` e `serving/sincronizar_d1_lib.py` para incluir `catalogo_nos_estrada` e `catalogo_distancias_estrada` no cálculo de deltas, no payload JSON e na sincronização D1, atualizar a documentação pertinente e verificar que todos os testes unitários e `mypy` passam com 100% de cobertura nos módulos alterados
