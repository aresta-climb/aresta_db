## Context

No algoritmo atual de `gerar_malha_estrada_pico` (`scripts/gerar_malha_estrada_lib.py`), cada nó `nid` era classificado em um único anel (`1`, `2` ou `3`) e filtrado por `distancias_estrada[nid] <= 200_000` e `dist_reta_km <= 150.0` **antes** de participar da eleição da célula `(anel, ix, iy)`. Isso produzia dois efeitos colaterais que reduziam a taxa de colisão entre picos próximos:
1. Quadrantes atravessados pelas circunferências de `15 km`, `60 km` ou `150 km` ou pela isolinha de `200 km` por estrada tinham metade de seus nós suprimidos antes da votação, elegendo um nó "vice-campeão" para um pico enquanto o pico vizinho elegia o vencedor verdadeiro do quadrante.
2. O grau de cruzamento usado no desempate (`len(adjacencia[nid])`) contava conexões com vias `residential`/`track` (`rank 5..6`, presentes apenas na BBox de `4 km`) ou `tertiary` (`rank 4`, presentes apenas na BBox de `60 km`), alterando o grau de nós de rodovias `tertiary` ou `secondary`/`primary` quando um pico estava a `< 4 km` (ou `< 60 km`) do nó e o outro pico estava a `> 4 km` (ou `> 60 km`).

## Goals / Non-Goals

**Goals:**
- Garantir que cada quadrante `(anel, ix, iy)` eleja seu vencedor intrínseco oficial considerando **todos** os nós alcançáveis daquele quadrado geográfico `[ix*passo, (ix+1)*passo) × [iy*passo, (iy+1)*passo)` com `rank <= rank_max`, sem recortar o quadrante ao meio.
- Incluir o vencedor intrínseco oficial de todo quadrante `(anel, ix, iy)` que seja alcançado dentro da faixa radial do anel e com pelo menos um nó elegível `<= 200 km` por estrada (`DISTANCIA_MAXIMA_ESTRADA_METROS`), preservando a distância e duração reais calculadas pelo Dijkstra até o nó vencedor.
- Estabilizar o cálculo do grau de cruzamento por camada hierárquica de BBox (`rank <= 3` conta vizinhos `rank <= 3`; `rank == 4` conta vizinhos `rank <= 4`; `rank >= 5` conta vizinhos `rank <= 6`).

**Non-Goals:**
- Alterar o schema Protobuf/SQLite ou o formato dos arquivos `malha_estrada.yaml`.
- Alterar o `rank_max = 6` do Anel 1 (`0–15 km`), preservando a resolução de estradas locais nos `4 km` em torno de cada pico.

## Decisions

### 1. Separação entre Eleição Intrínseca do Quadrante e Ativação do Quadrante pelo Pico
- Para cada configuração de anel `(anel, passo, rank_max)` em `((1, 0.02, 6), (2, 0.06, 4), (3, 0.18, 3))`:
  - Todo nó alcançável `nid in distancias_estrada` com `rank_rodovia[nid] <= rank_max` vota incondicionalmente no quadrante `chave_celula = (anel, math.floor(lat_no / passo), math.floor(lon_no / passo))` armazenado em `vencedores_intrinsecos_celula[chave_celula] = (prio, nid, dist_reta_km)`.
  - Separadamente, se o nó `nid` está dentro do limite rodoviário (`nid == no_pico or distancias_estrada[nid] <= DISTANCIA_MAXIMA_ESTRADA_METROS`) e sua distância em linha reta ao pico cai na faixa do anel (`<= 15 km` para Anel 1; `15–60 km` para Anel 2; `60–150 km` para Anel 3), o quadrante `(anel, ix, iy)` daquele anel (se `rank <= rank_max`) é marcado em `celulas_ativadas: set[tuple[int, int, int]]`.
  - Ao final, para cada `chave_celula` em `celulas_ativadas` (percorridas em ordem de anel `1, 2, 3`), o vencedor oficial `vencedores_intrinsecos_celula[chave_celula]` é adicionado a `ids_selecionados`.

### 2. Grau de Cruzamento Estável por Camada (`limite_rank_grau`)
- Como a consulta Overpass utiliza 3 BBoxes alinhadas por `rank` (`150 km` para `rank 1..3`, `60 km` para `rank 4`, `4 km` para `rank 5..6`), o grau de um nó de `rank <= 3` só é invariante ao deslocamento da BBox de `60 km` e `4 km` se contar apenas vizinhos de `rank <= 3`. Analogamente, o grau de um nó de `rank == 4` só é invariante ao deslocamento da BBox de `4 km` se contar apenas vizinhos de `rank <= 4`.
- Portanto, `limite_rank_grau = 3 if rank <= 3 else (4 if rank == 4 else 6)` elimina 100% das divergências de grau induzidas por bordas de BBox internas.

## Risks / Trade-offs

- **[Risco] Vencedor oficial de um quadrante de borda ter distância rodoviária ligeiramente superior a `200 km`** → **Mitigação**: A decisão foi alinhada explicitamente com o usuário ("eleger todos os quadrantes dentro de 200 km, mesmo que o ponto vencedor esteja um tico mais distante"). Como um quadrante de `0.18°` mede `~20 km`, qualquer quadrante ativado (que já possui nós `<= 200 km`) terá seu vencedor oficial no máximo `~200–220 km` por estrada, com distância e tempo reais já calculados pelo Dijkstra.
