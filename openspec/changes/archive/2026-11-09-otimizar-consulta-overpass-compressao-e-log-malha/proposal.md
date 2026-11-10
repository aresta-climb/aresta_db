# Proposal

## Why

A consulta atual à Overpass API realiza 4 varreduras radiais (`around:`) com forte sobreposição (buscando `motorway..secondary` 3 vezes e `tertiary` 2 vezes), transfere ~42 MB de JSON sem compressão HTTP (`Accept-Encoding`) e adiciona centenas de linhas repetidas de download no log do `DialogoProgressoMalhaEstrada`. Substituir os filtros radiais redundantes por 3 Bounding Boxes disjuntas (incluindo `unclassified` apenas no micro-anel de 4 km), negociar compressão moderna em streaming (`zstd, br, gzip, deflate`) com liberação de queries canceladas (`/api/kill_my_queries`) e atualizar a linha de download *in-place* reduzem drasticamente a latência na Overpass API, o volume trafegado e a poluição visual no Editor.

## What Changes

- **Query Overpass com 3 Bounding Boxes Disjuntas e Ordenação Quadtile (`qt`)**:
  - Substituir as 4 cláusulas `around:` sobrepostas em `construir_query_overpass` por 3 cláusulas disjuntas baseadas em Bounding Box `(sul, oeste, norte, leste)` e `out body qt; >; out skel qt;`:
    1. **BBox 4 km**: `residential|living_street|road|track|service|unclassified` (restrito ao acesso local imediato do pico);
    2. **BBox 60 km**: `tertiary|tertiary_link` (atendendo aos anéis de 15 km e 60 km sem repetição);
    3. **BBox 180 km**: `motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link` (atendendo aos 3 anéis de uma só vez).
  - Manter integralmente todos os nós das `ways` no grafo para preservar o determinismo de `prioridade_intrinseca_no` entre picos e a cobertura de estradas longas sem cruzamentos.
- **Negociação de Compressão (`zstd, br, gzip, deflate`), Espelhos Válidos e `/api/kill_my_queries`**:
  - Adicionar `zstandard` e `brotli` às dependências do projeto (`pyproject.toml`) e enviar `Accept-Encoding: zstd, br, gzip, deflate` em `ClienteOverpass.consultar_malha`, descomprimindo os blocos em streaming conforme o `Content-Encoding` retornado pelo servidor (`zstd`, `br`, `gzip`, `deflate` ou `identity`).
  - Substituir o espelho com certificado SSL inválido (`maps.mail.ru`) por `https://lz4.overpass-api.de/api/interpreter` e acionar `/api/kill_my_queries` em caso de cancelamento pelo usuário ou timeout de leitura para liberar imediatamente o slot do IP no servidor Overpass.
- **Atualização *In-Place* da Linha de Download no `DialogoProgressoMalhaEstrada`**:
  - Atualizar `DialogoProgressoMalhaEstrada._ao_progresso` para substituir a última linha do `QPlainTextEdit` quando a nova mensagem pertencer à mesma etapa contínua de recebimento (`"Recebendo malha viária..."`), evitando empilhar centenas de linhas no log.

## Capabilities

### New Capabilities

### Modified Capabilities
- `malha-estrada-osm-precomputada`: Atualiza os requisitos de consulta à Overpass API (3 Bounding Boxes disjuntas com `unclassified` restrito a 4 km, negociação de compressão `zstd, br, gzip, deflate` em streaming, liberação de slot via `kill_my_queries` e atualização *in-place* da linha de progresso de download no diálogo do Editor).

## Impact

- **`pyproject.toml` / `uv.lock`**: adição de `zstandard` e `brotli` nos grupos `deploy` e `editor`.
- **`scripts/gerar_malha_estrada_lib.py` e `scripts/gerar_malha_estrada_lib_test.py`**: refatoração de `construir_query_overpass`, descompressão em streaming (`zstd`, `br`, `gzip`, `deflate`) e `kill_my_queries` em `ClienteOverpass`.
- **`editor/views/widget_mensagem_coordenada.py` e `editor/views/widget_mensagem_coordenada_test.py`**: atualização *in-place* da linha de progresso de download em `DialogoProgressoMalhaEstrada._ao_progresso`.
