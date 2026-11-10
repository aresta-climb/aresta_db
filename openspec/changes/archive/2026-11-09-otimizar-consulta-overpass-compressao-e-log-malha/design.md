# Design

## Context

Veja `proposal.md` para a motivação. Na implementação atual de `scripts/gerar_malha_estrada_lib.py` e `editor/views/widget_mensagem_coordenada.py`:
1. `construir_query_overpass` emite 4 filtros radiais `around:R,lat,lon` com sobreposição das mesmas classes de rodovia (`motorway..secondary` consultadas 3 vezes; `tertiary` consultadas 2 vezes) e sem ordenação por quadtile (`qt`) no `out body`.
2. `ClienteOverpass.consultar_malha` utiliza `urllib.request` sem cabeçalho `Accept-Encoding`, transferindo ~42 MB de JSON descomprimido, inclui o espelho `maps.mail.ru` (cujo certificado TLS está inválido) e não invoca `/api/kill_my_queries` quando uma requisição é abortada no cliente.
3. `DialogoProgressoMalhaEstrada._ao_progresso` chama `self.lista_etapas.appendPlainText(...)` a cada bloco de 64 KB recebido, gerando centenas de linhas quase idênticas no `QPlainTextEdit`.

## Goals / Non-Goals

**Goals:**
- Reduzir o custo de CPU/disco da query na Overpass API usando 3 Bounding Boxes `(sul, oeste, norte, leste)` disjuntas e `out body qt; >; out skel qt;`, movendo `unclassified` para o micro-anel local de `4 km`.
- Negociar `Accept-Encoding: zstd, br, gzip, deflate` e descomprimir em streaming a cada bloco lido de `64 KB` (`zstandard`, `brotli`, `zlib`), reduzindo o tráfego de rede em 5x–8x.
- Liberar slots pendurados no servidor Overpass via `/api/kill_my_queries` em cancelamentos ou timeouts e atualizar a lista de espelhos padrão (`overpass-api.de`, `lz4.overpass-api.de`, `overpass.private.coffee`).
- Atualizar *in-place* a última linha do log em `DialogoProgressoMalhaEstrada._ao_progresso` quando a mensagem em curso for uma atualização de `"Recebendo malha viária"`.

**Non-Goals:**
- Não descartar nem contrair nós intermediários de grau 2 (`ways`), preservando 100% da cobertura em estradas longas sem cruzamentos e o determinismo de `prioridade_intrinseca_no`.

## Decisions

### 1. Particionamento em 3 Bounding Boxes Disjuntas + `out body qt`
- **Decisão**: Criar uma função auxiliar `_calcular_bbox_graus(latitude: float, longitude: float, raio_km: float) -> str` que converte o raio em quilômetros para `"sul,oeste,norte,leste"` usando $\Delta\text{lat} = \frac{R}{111.32}$ e $\Delta\text{lon} = \frac{R}{111.32 \times \max(0.01, \cos(\text{lat}))}$, e estruturar `construir_query_overpass` com 3 uniões disjuntas:
  - `4 km`: `residential|living_street|road|track|service|unclassified`
  - `60 km`: `tertiary|tertiary_link`
  - `180 km`: `motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link`
  Finalizando com `out body qt;\n>;\nout skel qt;\n`.
- **Racional**: O índice espacial interno da Overpass (Quadtile) resolve Bounding Boxes diretamente sem cálculo trigonométrico por coordenada, e particionar os valores de `highway` em 3 conjuntos disjuntos evita que qualquer rodovia seja varrida mais de uma vez. A filtragem circular exata de `15 km`, `60 km` e `180 km` continua sendo feita em Python por `calcular_distancia_haversine_metros` durante a amostragem dos 3 anéis (com `rank_max = 5` para o anel 1 já aceitando `tertiary` e `secondary`, e `unclassified` disponível nos primeiros 4 km onde há conexão do estacionamento até a malha principal).

### 2. Descompressão Incremental em Streaming (`zstd`, `br`, `gzip`, `deflate`)
- **Decisão**: Adicionar `zstandard` e `brotli` nos grupos `deploy` e `editor` do `pyproject.toml` e implementar `_criar_descompressor_streaming(content_encoding: str | None)` em `scripts/gerar_malha_estrada_lib.py`:
  - `zstd`: `zstandard.ZstdDecompressor().decompressobj()`
  - `br`: `brotli.Decompressor()` (usando `.process(bloco)`)
  - `gzip`: `zlib.decompressobj(16 + zlib.MAX_WBITS)`
  - `deflate`: `zlib.decompressobj()`
  - vazio / `identity`: repasse direto dos bytes.
  Cada bloco de `65536` bytes lido de `resposta.read(65536)` contabiliza `total_bytes_rede` (exibido em MB na mensagem de progresso) e alimenta imediatamente o descompressor em streaming.
- **Racional**: Permite leitura progressiva e cancelamento cooperativo a cada 64 KB trafegados sem precisar aguardar o download inteiro e negociando o algoritmo mais compacto suportado pelo espelho.

### 3. Liberação de Queries Pendentes (`/api/kill_my_queries`) e Espelhos Padrão
- **Decisão**: Atualizar `ESPELHOS_OVERPASS_PADRAO` para `("https://overpass-api.de/api/interpreter", "https://lz4.overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter")` e adicionar `_encerrar_queries_pendentes_espelho(url_interpreter: str)` (chamada com timeout curto de `3s`, ignorando erros de rede) sempre que `ErroMalhaEstradaCancelada` ou `TimeoutError`/`URLError` ocorrer durante a consulta a um espelho.
- **Racional**: Evita que uma query cancelada ou que sofreu timeout continue ocupando o slot do IP no servidor da Overpass por 120s.

### 4. Atualização *In-Place* da Linha de Download no `DialogoProgressoMalhaEstrada`
- **Decisão**: Em `DialogoProgressoMalhaEstrada._ao_progresso(mensagem, percentual)`, manter o controle se a última linha inserida em `self.lista_etapas` é uma linha de progresso de download (`mensagem.startswith("Recebendo malha viária")`). Quando tanto a linha anterior quanto a nova mensagem começarem com `"Recebendo malha viária"`, substituir o último bloco do `QPlainTextEdit` via `QTextCursor` (`MoveOperation.End` + `SelectionType.BlockUnderCursor` + `insertText`) em vez de chamar `appendPlainText`.
- **Racional**: Mantém o log de etapas limpo (apenas 1 linha para o download que avança de `0.1 MB` até o total recebido), preservando todas as demais etapas no histórico.

## Risks / Trade-offs

- **[Risk] Servidor intermediário retornar `Content-Encoding` desconhecido ou múltiplos encodings** → Mitigação: normalizar `Content-Encoding` em minúsculas e tratar `zstd`, `br`, `gzip` e `deflate`; se um servidor ignorar o header, o fallback `identity` processa o JSON normalmente.
- **[Risk] Chamada a `/api/kill_my_queries` atrasar o cancelamento se o servidor estiver inacessível** → Mitigação: usar timeout máximo de `2.0s` e suprimir qualquer exceção de rede no `kill_my_queries` para não bloquear o fechamento da janela nem o failover para o próximo espelho.
