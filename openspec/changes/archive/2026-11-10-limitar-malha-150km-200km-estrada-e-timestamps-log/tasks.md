# Tasks

## 1. Anel 3 de `150 km`, Teto de `200 km` por Estrada e Log de Failover (`gerar_malha_estrada_lib.py`)

- [x] 1.1 Atualizar e escrever testes em `scripts/gerar_malha_estrada_lib_test.py` validando: (a) BBox externa de `150 km` mantendo `secondary|secondary_link` e `ESPELHOS_OVERPASS_PADRAO` com `lz4.overpass-api.de`, `overpass.private.coffee` e `z.overpass-api.de`; (b) exclusão de nós com `distancia_metros > 200_000` (`200 km` por estrada) ou `dist_reta_km > 150.0` na amostragem do Anel 3; e (c) emissão de mensagem de progresso explícita (`"Falha em ... tentando próximo espelho..."`) quando um espelho falha e aciona failover (Red)
- [x] 1.2 Implementar o raio de `150 km` no Anel 3, o filtro `DISTANCIA_MAXIMA_ESTRADA_METROS = 200_000.0`, a nova lista `ESPELHOS_OVERPASS_PADRAO` e o aviso de progresso no failover em `scripts/gerar_malha_estrada_lib.py`, verificando 100% de cobertura com `pytest` (Green)

## 2. Timestamps e Tempo Decorrido no `DialogoProgressoMalhaEstrada` (`widget_mensagem_coordenada.py`)

- [x] 2.1 Escrever teste em `editor/views/widget_mensagem_coordenada_test.py` validando que cada linha adicionada em `DialogoProgressoMalhaEstrada.lista_etapas` inclui o prefixo de timestamp e tempo decorrido (`[HH:MM:SS +X.Xs] [XX%] ...`) e que atualizações consecutivas de `"Recebendo malha viária de ..."` continuam atualizando a mesma linha *in-place* (Red)
- [x] 2.2 Implementar o prefixo `[HH:MM:SS +X.Xs]` com atualização *in-place* em `DialogoProgressoMalhaEstrada._ao_progresso` (`editor/views/widget_mensagem_coordenada.py`) e validar 100% de cobertura com `pytest` (Green)
