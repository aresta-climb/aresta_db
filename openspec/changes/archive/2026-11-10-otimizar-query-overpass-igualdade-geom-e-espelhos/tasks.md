# Tasks

## 1. Otimização da Query Overpass, Leitura de `geometry` Inline e Ordem de Espelhos

- [x] 1.1 Atualizar `scripts/gerar_malha_estrada_lib_test.py` para validar: (a) `ESPELHOS_OVERPASS_PADRAO` na ordem `lz4.overpass-api.de`, `z.overpass-api.de`, `overpass.private.coffee` e `timeout_segundos == 60`; (b) `construir_query_overpass` com `[out:json][timeout:60];`, cláusulas de igualdade exata `["highway"="..."]` nas 3 bboxes e sufixo `out geom qt;` (sem `>;` e sem `out skel qt;`); e (c) `_extrair_grafo_maior_componente` / `gerar_malha_estrada_pico` construindo o grafo e calculando `distancia_metros` e `duracao_minutos` diretamente a partir de `ways` com `geometry` inline (Red)
- [x] 1.2 Implementar as alterações em `scripts/gerar_malha_estrada_lib.py` e validar 100% de cobertura com `pytest`, `ruff` e `mypy` (Green)
