# Proposal

## Why

Ao testar manualmente a geração do mapa de pontos na Gruta da Lapinha com as 3 Bounding Boxes e compressão, identificamos três oportunidades diretas de melhoria:
1. **Excesso de raio em linha reta (`180 km`) gerando caminhos de até `350,7 km` por estrada**: Como o limite de cobertura da malha para estimativa de tempo no app é de **200 km por estrada** (`distancia_metros <= 200_000`) e o fator de sinuosidade rodoviária médio é de `1,3x` a `1,5x`, uma Bounding Box de `±180 km` em linha reta ($360 \times 360\text{ km} = 129.600\text{ km}^2$, chegando a $254\text{ km}$ nas diagonais) busca ~30% a mais de área do que o necessário e inclui mais de 100 nós com distância entre `200 km` e `350 km` por estrada. Reduzir o Anel 3 e sua Bounding Box para **`150 km` em linha reta** ($300 \times 300\text{ km} = 90.000\text{ km}^2$, alcançando $212\text{ km}$ nas diagonais) mantendo `secondary` e aplicando o teto explícito de **`200 km` por estrada** (`distancia_metros <= 200_000`) reduz significativamente o custo na Overpass API sem perder nenhuma rodovia estadual (`MG-*`) ou travessia urbana.
2. **Falta de timestamps no log de progresso do `DialogoProgressoMalhaEstrada`**: Sem o horário ou tempo decorrido (`+Xs`) em cada linha do histórico textual, não fica visível quanto tempo foi gasto aguardando a Overpass API (TTFB), transferindo os pacotes na rede ou processando o grafo em Python.
3. **Failover silencioso e DNS round-robin em `overpass-api.de`**: Quando `overpass-api.de` sorteia o nó `z.overpass-api.de` e este retorna erro (`HTTP 502` ou timeout), o cliente aguarda e passa silenciosamente para o próximo espelho sem registrar o motivo no log. Priorizar os endpoints diretos (`lz4.overpass-api.de`, `overpass.private.coffee`, `z.overpass-api.de`) e emitir uma linha explícita no log quando um espelho falha torna o diagnóstico imediato.

## What Changes

- **Redução do Anel 3 para `150 km` em linha reta e teto de `200 km` por estrada (`scripts/gerar_malha_estrada_lib.py`)**:
  - Ajustar a 3ª Bounding Box de `construir_query_overpass` e o limite do Anel 3 na amostragem de `180 km` para **`150 km`**, mantendo integralmente `motorway`, `trunk`, `primary` e `secondary` (e respectivos `*_link`).
  - Definir `DISTANCIA_MAXIMA_ESTRADA_METROS = 200_000.0` (`200 km` por estrada) e filtrar na amostragem dos anéis quaisquer nós com `distancias_estrada[nid] > DISTANCIA_MAXIMA_ESTRADA_METROS` (exceto `no_pico`), garantindo que a malha gerada respeite o limite de 200 km por estrada e que os portais de borda (`na_borda = 1`) fiquem posicionados na fronteira real de até 200 km por estrada.
- **Ordem de espelhos diretos e notificação explícita de failover (`scripts/gerar_malha_estrada_lib.py`)**:
  - Atualizar `ESPELHOS_OVERPASS_PADRAO` para usar os hosts diretos `lz4.overpass-api.de`, `overpass.private.coffee` e `z.overpass-api.de` (evitando o round-robin ambíguo de `overpass-api.de`).
  - Quando um espelho falhar e houver próximo espelho na lista de failover, emitir uma mensagem de progresso informando a falha no espelho antes de tentar o próximo (`"Falha em <host> (<motivo>), tentando próximo espelho..."`).
- **Timestamps e tempo decorrido no log do `DialogoProgressoMalhaEstrada` (`editor/views/widget_mensagem_coordenada.py`)**:
  - Prefixar cada linha do histórico `lista_etapas` com o horário local e o tempo decorrido desde o início da geração (formato `[HH:MM:SS +X.Xs] [XX%] Mensagem...`), preservando a atualização *in-place* da linha de recebimento (`"Recebendo malha viária de ..."`).

## Capabilities

### New Capabilities
- *(Nenhuma nova capability)*

### Modified Capabilities
- `malha-estrada-osm-precomputada`: Atualiza a BBox e o raio do Anel 3 para `150 km` em linha reta com teto de `200 km` de distância acumulada por estrada, adiciona log explícito de failover entre espelhos diretos e inclui timestamps com tempo decorrido no log do `DialogoProgressoMalhaEstrada`.

## Impact

- **`aresta_db`**:
  - `scripts/gerar_malha_estrada_lib.py` e `scripts/gerar_malha_estrada_lib_test.py`
  - `editor/views/widget_mensagem_coordenada.py` e `editor/views/widget_mensagem_coordenada_test.py`
