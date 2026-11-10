# Design

## Context

Veja `proposal.md`. A geração do mapa de pontos na Gruta da Lapinha evidenciou que:
1. A Bounding Box do Anel 3 com `180 km` em linha reta cobre um quadrado de $360 \times 360\text{ km}$ ($129.600\text{ km}^2$, até $254\text{ km}$ nas diagonais) e produz nós com até `350,7 km` de distância por estrada, embora o limite funcional da malha seja **`200 km` por estrada** (`200.000 m`).
2. O domínio `overpass-api.de` faz DNS round-robin entre `lz4.overpass-api.de` e `z.overpass-api.de`; quando cai em um nó degradado (`502 Bad Gateway` ou timeout), o failover ocorria sem registrar mensagem no log.
3. O log do `DialogoProgressoMalhaEstrada` não exibia timestamps nem o tempo decorrido (`+Xs`), dificultando identificar quanto tempo cada fase demorou.

## Goals / Non-Goals

**Goals:**
- Reduzir a BBox e o corte geográfico do Anel 3 de `180 km` para **`150 km` em linha reta** ($300 \times 300\text{ km} = 90.000\text{ km}^2$, `-30,6%` de área), mantendo `secondary` e `secondary_link` no Anel 3.
- Limitar os nós amostrados na malha a **`DISTANCIA_MAXIMA_ESTRADA_METROS = 200_000.0`** (`200 km` por estrada).
- Substituir `overpass-api.de` em `ESPELHOS_OVERPASS_PADRAO` pelos hosts diretos (`lz4.overpass-api.de`, `overpass.private.coffee`, `z.overpass-api.de`) e emitir mensagem de progresso explícita quando um espelho falhar antes do failover.
- Adicionar timestamp e tempo decorrido (`[HH:MM:SS +X.Xs]`) a todas as entradas do log em `DialogoProgressoMalhaEstrada`, preservando a atualização *in-place* da linha de download.

**Non-Goals:**
- Remover `secondary` do Anel 3 (pois rodovias estaduais `MG-*` e travessias urbanas utilizam `secondary`).
- Alterar o contrato Protobuf ou o app Flutter.

## Decisions

### 1. Anel 3 de `150 km` em Linha Reta e Limite de `200 km` por Estrada
- **Decisão**:
  - Em `construir_query_overpass`: usar `bbox_150km = _calcular_bbox_graus(latitude, longitude, 150.0)` para `motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link`.
  - Definir `RAIO_ANEL_3_KM = 150.0` e `DISTANCIA_MAXIMA_ESTRADA_METROS = 200_000.0`.
  - Na etapa 3 de `gerar_malha_estrada_pico`: para todo `nid != no_pico`, se `distancias_estrada[nid] > DISTANCIA_MAXIMA_ESTRADA_METROS`, ignorar o nó antes da eleição por célula, e usar `elif dist_reta_km <= RAIO_ANEL_3_KM:` para o Anel 3.
- **Racional**: $150\text{ km}$ em linha reta (com até $212\text{ km}$ nas diagonais da BBox) cobre integralmente os caminhos reais de até $200\text{ km}$ por estrada e reduz em mais de 30% a área varrida pelo Overpass. O filtro `distancias_estrada[nid] <= 200_000.0` elimina os ~20% de nós excedentes (entre 200 e 350 km por estrada) e posiciona os 8 portais de borda exatamente na fronteira dos 200 km por estrada.

### 2. Espelhos Diretos e Log Explícito de Failover
- **Decisão**:
  - Definir:
    ```python
    ESPELHOS_OVERPASS_PADRAO: tuple[str, ...] = (
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
        "https://z.overpass-api.de/api/interpreter",
    )
    ```
  - Em `ClienteOverpass.consultar_malha`: quando a tentativa no espelho `idx` levantar `HTTPError` ou `(URLError, TimeoutError)` e houver um próximo espelho (`idx + 1 < len(self.urls_endpoints)`), chamar `_notificar_progresso` com `f"Falha em {host} ({motivo}), tentando próximo espelho..."` no percentual `16` antes de prosseguir para o próximo espelho.

### 3. Timestamps e Tempo Decorrido no `DialogoProgressoMalhaEstrada`
- **Decisão**:
  - No `__init__` de `DialogoProgressoMalhaEstrada`, registrar `self._instante_inicio = time.monotonic()`.
  - Em `_ao_progresso(self, mensagem: str, percentual: int)`:
    - Calcular `decorrido = max(0.0, time.monotonic() - self._instante_inicio)` e `horario = datetime.now().strftime("%H:%M:%S")`.
    - Formatar `nova_linha = f"[{horario} +{decorrido:.1f}s] [{percentual}%] {mensagem}"`.
    - Na verificação de substituição *in-place* da linha de recebimento (`"Recebendo malha viária de "`), verificar se `mensagem.startswith("Recebendo malha viária de ")` e se a última linha existente em `lista_etapas` contém `"] Recebendo malha viária de "`, substituindo-a *in-place* com o novo timestamp e megabytes atualizados.
