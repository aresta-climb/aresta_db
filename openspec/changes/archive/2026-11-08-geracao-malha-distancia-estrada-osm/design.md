# Design

## Context

Conforme descrito em `proposal.md`, o contrato em `aresta_api` (`sql/catalogo.sql` e `openapi/catalogo.yaml`) e o cliente móvel em `aresta_app` já estão prontos para armazenar, sincronizar e consultar as tabelas `catalogo_nos_estrada` e `catalogo_distancias_estrada`. No `aresta_db`, precisamos construir a ponta geradora que extrai o grafo viário do OpenStreetMap, calcula as distâncias por estrada até cada pico, persiste esses dados de forma incremental no `catalogo.db` e propaga os deltas para o Cloudflare D1.

## Goals / Non-Goals

**Goals:**
- Implementar a extração da malha viária do OpenStreetMap e o algoritmo de Dijkstra + amostragem em 3 anéis concêntricos usando **apenas a biblioteca padrão do Python (`urllib.request`, `heapq`, `math`, `zlib`)**, sem introduzir dependências nativas pesadas como `osmnx`, `gdal` ou `networkx`.
- Isolar a fronteira HTTP com a Overpass API por meio de um protocolo claro e uma biblioteca `scripts/cliente_overpass_fake.py` testada 1:1 (Princípio V do `AGENTS.md`).
- Preservar a malha rodoviária já calculada em `catalogo.db` durante edições comuns de vias/setores/textos em `gerar_catalogo_completo`, evitando requisições de rede desnecessárias e recomputações quando a coordenada do pico não mudou.
- Incluir `catalogo_nos_estrada` e `catalogo_distancias_estrada` no cálculo de `versao_catalogo`, nos diffs SQL (`gerar_deltas_catalogo.py`) e na sincronização com o Cloudflare D1 (`serving/sincronizar_d1_lib.py`).

**Non-Goals:**
- Alterar o esquema Protobuf (`croqui.proto` / `indice.proto`), pois a malha rodoviária trafega exclusivamente pelo `catalogo.db` e pelo endpoint `/sync`.
- Executar chamadas de rede reais à Overpass API durante a suíte de testes automatizados (`pytest`).

## Decisions

### 1. Grafo Viário e Dijkstra Invertido em Python Puro (Zero Dependências Externas Pesadas)
- **Decisão**: Implementar o parser da resposta JSON da Overpass API, a filtragem do maior componente conexo e o algoritmo de Dijkstra em Python puro (`heapq` + fórmula de Haversine) dentro de `scripts/gerar_malha_estrada_lib.py`.
- **Racional**:
  - Bibliotecas como `osmnx` exigem `geopandas`, `shapely`, `proj` e `gdal`, que tornam o ambiente pesado e frágil em Windows/macOS/Linux (especialmente no empacotamento PyInstaller do Editor).
  - Uma única query Overpass QL buscando `way["highway"~"..."]` com `out body; >; out skel qt;` retorna todos os `nodes` (com `id`, `lat`, `lon`) e `ways` (com lista de `nodes` e tag `highway`). Construir a lista de adjacência e rodar `heapq` para ~20k–80k nós leva poucos milissegundos em Python puro.
- **Query Overpass QL**:
  Para evitar baixar milhões de ruas residenciais distantes, a query Overpass combina três cláusulas `around` na mesma requisição:
  1. `0–15 km` (`around:15000`): `motorway|trunk|primary|secondary|tertiary|unclassified|residential|track|service` (mais `*_link`).
  2. `15–60 km` (`around:60000`): `motorway|trunk|primary|secondary|tertiary` (mais `*_link`).
  3. `60–180 km` (`around:180000`): `motorway|trunk|primary|secondary` (mais `*_link`).

### 2. Filtragem do Maior Componente Conexo e Nó do Estacionamento (`no_pico`)
- **Decisão**: Antes de localizar o nó mais próximo à coordenada `(lat, lon)` do pico, particionar o grafo não-direcionado em componentes conexos (via BFS/DFS) e reter apenas o maior componente conexo.
- **Racional**: Em regiões de montanha, o OpenStreetMap frequentemente possui pequenos trechos de `track` ou `service` mapeados de forma isolada (sem conexão com a rodovia). Se escolhêssemos o nó geometricamente mais próximo sem filtrar o maior componente conexo, o Dijkstra ficaria preso na ilha isolada.
- O nó do maior componente conexo mais próximo da coordenada do pico (`no_pico`) recebe `distancia_metros = 0` e é sempre incluído na saída do croqui.

### 3. Amostragem Determinística em 3 Anéis Concêntricos ($3 \times 3$) e Portais de Borda
- **Decisão**:
  - Classificar os nós alcançáveis pelo Dijkstra de acordo com a distância geodésica ao pico em 3 anéis:
    - **Anel 1 ($d \le 15\text{ km}$)**: passo de grade `0.02°`, aceita qualquer `rank_rodovia` ($1 \dots 6$).
    - **Anel 2 ($15\text{ km} < d \le 60\text{ km}$)**: passo de grade `0.06°`, aceita `rank_rodovia <= 4` (até `tertiary`).
    - **Anel 3 ($60\text{ km} < d \le 180\text{ km}$)**: passo de grade `0.18°`, aceita `rank_rodovia <= 3` (até `secondary`).
  - Em cada célula `(math.floor(lat / passo), math.floor(lon / passo))`, eleger o único nó vencedor que minimiza a tupla:
    $$\text{prioridade}(\text{nó}) = \big(\text{rank\_rodovia},\; -\text{grau\_cruzamento},\; \text{zlib.crc32}(str(\text{no\_osm\_id}).encode())\big)$$
  - **Portais de Borda (`na_borda = 1`)**: Dividir os nós amostrados no anel mais externo disponível do pico em 8 octantes direcionais ($0 \dots 7$, cada um de $45^\circ$ a partir do pico) e marcar como portal (`na_borda = 1`) o nó mais externo (maior distância geodésica ao pico, desempatando por menor prioridade intrínseca) em cada octante ocupado.

### 4. Persistência Incremental em `gerar_catalogo_sqlite_lib.py`
- **Decisão**:
  - `gerar_catalogo_completo` recebe um parâmetro opcional `cliente_overpass: ClienteOverpassProtocolo | None = None` (e `recalcular_malha_estrada: bool = False`).
  - Quando um croqui existente tem seus metadados de `catalogo_croquis` ou `catalogo_aresta` atualizados durante uma compilação normal, `remover_croqui_do_catalogo(..., preservar_malha_estrada=True)` preserva suas linhas em `catalogo_distancias_estrada`.
  - Quando um croqui é efetivamente removido do catálogo (ou despublicado), suas linhas em `catalogo_distancias_estrada` são excluídas e os nós órfãos em `catalogo_nos_estrada` (`WHERE no_osm_id NOT IN (SELECT DISTINCT no_osm_id FROM catalogo_distancias_estrada)`) são limpos automaticamente.
  - Quando `cliente_overpass` é fornecido e um croqui publicado com coordenada válida ainda não possui registros em `catalogo_distancias_estrada` (ou `recalcular_malha_estrada=True`), a malha do croqui é gerada e persistida em `catalogo_nos_estrada` e `catalogo_distancias_estrada`.

## Risks / Trade-offs

- **[Rate limit ou lentidão da Overpass API ao processar dezenas de picos]** → `ClienteOverpassHttp` suporta lista de endpoints espelho da Overpass API com timeout configurável, e a persistência incremental no `catalogo.db` garante que apenas picos novos (sem registros em `catalogo_distancias_estrada`) consultem a rede.
- **[Compatibilidade com testes existentes de `gerar_catalogo_sqlite_lib_test.py`]** → Como `cliente_overpass` tem padrão `None`, todos os testes existentes continuam executando instantaneamente e 100% offline, enquanto os novos testes injetam `ClienteOverpassFake`.
