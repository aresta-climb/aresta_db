# Design

## Context

No banco de dados interno do Overpass (`ways_tags_local.bin`), o índice de tags opera sobre pares exatos `(key, value)`. O uso de regex (`["highway"~"^(...)$"]`) sobre caixas grandes (`60 km` e `150 km`) obriga o servidor a varrer todas as `ways` com a chave `"highway"` na região inteira. Além disso, `out geom qt;` dispensa o segundo passo `>; out skel qt;` porque o Overpass já armazena as coordenadas dos vértices junto a cada `way`, entregando `"nodes": [id1, id2, ...]` e `"geometry": [{"lat": ..., "lon": ...}, ...]` pareados na mesma lista de elementos.

## Goals / Non-Goals

**Goals:**
- Reduzir o tempo de processamento no servidor Overpass de `~73s` para `~38s` usando igualdades exatas (`["highway"="..."]`) e `out geom qt;`.
- Preservar 100% dos dados do grafo (`no_osm_id`, coordenadas `(lat, lon)`, `tags` das `ways`, `distancia_metros` e `duracao_minutos`).
- Priorizar `lz4.overpass-api.de` e `z.overpass-api.de` antes de `overpass.private.coffee`, reduzindo o timeout por tentativa para `60s`.

**Non-Goals:**
- Alterar o algoritmo de Dijkstra, as velocidades sem trânsito ou os raios dos 3 anéis.

## Decisions

### 1. Estrutura da Query Overpass QL
- Cabeçalho `[out:json][timeout:60];`.
- Para cada tipo de `highway` em `4 km`, `60 km` e `150 km`, emitir cláusulas de igualdade exata `way["highway"="<tipo>"](<bbox>);` dentro do bloco de união `(...)`, seguidas por `out geom qt;`.

### 2. Leitura Híbrida de Coordenadas em `_extrair_grafo_maior_componente`
- Popula `coordenadas[no_osm_id] = (lat, lon)` tanto a partir de elementos `type == "node"` quanto a partir dos pares `zip(elem["nodes"], elem["geometry"])` presentes em cada elemento `type == "way"`.
- Dessa forma, respostas reais com `out geom qt;` dispensam qualquer elemento `node` separado, e os testes existentes com `type == "node"` continuam funcionando sem perda de cobertura.
