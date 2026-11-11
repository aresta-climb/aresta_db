# Proposal

## Why

A análise empírica dos logs com timestamps revelou que `98,8%` do tempo de geração da malha rodoviária (`194,6s` de `196,9s` totais na Gruta da Lapinha) ocorre aguardando a resposta da Overpass API, por três causas combinadas:
1. O uso do operador de expressão regular (`["highway"~"^(...)$"]`) nas Bounding Boxes de `60 km` e `150 km` (`90.000 km²`) impede o motor C++ do Overpass de usar seu índice direto por par `("highway", "<valor>")`, forçando a leitura e avaliação de regex sobre centenas de milhares de `ways` (incluindo vias `residential`, `service`, `footway` e `path` de toda a região metropolitana).
2. O sufixo `out body qt; >; out skel qt;` força uma segunda passagem de disco (`>;` recurse down) na tabela `nodes` do Overpass para buscar `~341.000` registros separados, enquanto `out geom qt;` já entrega em cada `way` tanto `"nodes": [id1, id2, ...]` quanto `"geometry": [{"lat": ..., "lon": ...}, ...]` diretamente a partir do armazenamento inline de `ways`.
3. A ordem dos espelhos tinha `overpass.private.coffee` antes de `z.overpass-api.de` com `timeout=120s`, desperdiçando `121s` em timeout quando o primeiro espelho alemão (`lz4.overpass-api.de`) recusava imediatamente por falta de slot livre.

## What Changes

- **Igualdades Exatas Indexadas e `out geom qt;` na Query Overpass**:
  - Substituir as cláusulas regex das caixas de `60 km` e `150 km` em `construir_query_overpass` por igualdades exatas (`way["highway"="tertiary"](bbox_60km);`, `way["highway"="motorway"](bbox_150km);`, etc.) para acionar o índice direto `(key, value)` do Overpass.
  - Substituir `out body qt; >; out skel qt;` por `out geom qt;` e declarar `[timeout:60]` no cabeçalho da query.
- **Extração de Coordenadas Inline (`geometry`) em `_extrair_grafo_maior_componente`**:
  - Ler as coordenadas `(lat, lon)` diretamente do array `geometry` pareado com `nodes` de cada `way` retornada por `out geom qt;` (mantendo suporte a elementos `type == "node"` para compatibilidade com fixtures de teste existentes), preservando 100% dos IDs OSM (`no_osm_id`), distâncias em metros e tempos em minutos.
- **Ordem de Espelhos e Timeout de Failover**:
  - Reordenar `ESPELHOS_OVERPASS_PADRAO` para priorizar os dois clusters oficiais alemães (`lz4.overpass-api.de`, `z.overpass-api.de` e depois `overpass.private.coffee`) e reduzir o timeout padrão de `ClienteOverpass` de `120s` para `60s`.

## Capabilities

### New Capabilities

*(Nenhuma)*

### Modified Capabilities
- `malha-estrada-osm-precomputada`: Atualizar o requisito de extração Overpass para refletir igualdades exatas indexadas (`["highway"="..."]`), saída `out geom qt;`, suporte a `geometry` inline nas `ways` e ordem de espelhos (`lz4.overpass-api.de`, `z.overpass-api.de`, `overpass.private.coffee`).

## Impact

- **`scripts/gerar_malha_estrada_lib.py` e `scripts/gerar_malha_estrada_lib_test.py`**: Atualização de `ESPELHOS_OVERPASS_PADRAO`, `TIMEOUT_PADRAO_OVERPASS_SEGUNDOS = 60`, `construir_query_overpass` e `_extrair_grafo_maior_componente`.
