## Context

As malhas geradas anteriormente usavam velocidades de cruzeiro otimistas (`motorway=95`, `trunk=80`, `primary=70 km/h`, `0.85 × maxspeed`) sem distinguir trechos urbanos (`lit=yes` ou `maxspeed <= 60`), estradas rurais `unclassified` sem pavimento explícito e atrasos em interseções (`grau >= 3`). Isso gerava tempos ~25% abaixo da realidade no percurso Belo Horizonte → Gruta do Baú (`48 min` em vez de `~60–65 min`) e Gruta da Lapinha (`51 min` em vez de `~65–70 min`).

## Goals / Non-Goals

**Goals:**
- Calibrar `calcular_velocidade_sem_transito_kmh` para refletir velocidades médias reais em fluxo normal, distinguindo asfalto rodoviário, vias urbanas iluminadas/limitadas a `60 km/h`, rotatórias e estradas rurais/de terra.
- Adicionar penalidade determinística por interseção (`grau >= 3`) em `_extrair_grafo_maior_componente` sem aumentar a complexidade assintótica do Dijkstra.
- Incrementar `VERSAO_ATUAL_MALHA_ESTRADA = 3` e regenerar as malhas publicadas.

**Non-Goals:**
- Consumir APIs externas de trânsito em tempo real (o catálogo continua 100% pré-computado e offline).

## Decisions

### 1. Modelo Hierárquico de Velocidade Efetiva por Tags OSM
Em `calcular_velocidade_sem_transito_kmh(tags)`:
1. `highway == "track"` → `15.0 km/h`.
2. Superfície não pavimentada (`surface in SUPERFICIES_NAO_PAVIMENTADAS` ou `tracktype in {"grade2", "grade3", "grade4", "grade5"}`) → `24.0 km/h` em `primary..tertiary` (e `*_link`) ou `18.0 km/h` nas demais.
3. `highway == "unclassified"` sem `surface in SUPERFICIES_PAVIMENTADAS` e sem `lit` urbano → `22.0 km/h` (vicinal rural).
4. Contexto urbano (`lit in {"yes", "true", "24/7", "automatic"}`, `highway in {"residential", "living_street", "service", "road"}` ou `maxspeed_num <= 60`):
   - Limite de placa urbano `limite_placa = min(60.0, maxspeed_num)` (ou base urbana da classe quando `maxspeed` ausente).
   - Velocidade efetiva = `max(15.0, min(teto_urbano_classe, limite_placa * 0.62))` (e limitada a `25.0 km/h` em `junction in {"roundabout", "circular"}`).
5. Rodovia intermunicipal pavimentada:
   - Tetos por classe: `motorway=82`, `motorway_link=45`, `trunk=68`, `trunk_link=40`, `primary=58`, `primary_link=38`, `secondary=46`, `secondary_link=34`, `tertiary=36`, `tertiary_link=28`, `unclassified=30`.
   - Com `maxspeed_num > 60`: `max(15.0, min(teto_rodovia, maxspeed_num * 0.74))` (e `<= 25.0 km/h` se rotatória).

### 2. Penalidade Simétrica de Interseção em Nós `grau >= 3`
Após montar `adjacencia` em `_extrair_grafo_maior_componente`:
- Para cada aresta `(u, v)`, soma-se ao `tempo_seg` o atraso de meia interseção de `u` e de `v`, onde um nó `w` com `len(adjacencia[w]) >= 3` adiciona `2.0s` se `melhor_rank[w] >= 2` (equivalente a `+4.0s` ao atravessar um cruzamento `u -> w -> v`) ou `1.0s` se `melhor_rank[w] == 1` (`+2.0s` em trevos/acessos de `trunk`/`motorway`).

## Risks / Trade-offs

- **[Trade-off] Malhas existentes na `v2` passam a ser sinalizadas como defasadas (`v2 -> v3`)** → **Mitigação**: Apenas 2 croquis possuem malha publicada hoje (Gruta da Lapinha e Gruta do Baú) e ambos serão regenerados e publicados neste mesmo deploy.
