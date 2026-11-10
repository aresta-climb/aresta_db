# Tasks

## 1. Dependências de Compressão (`zstandard` e `brotli`)

- [x] 1.1 Adicionar `zstandard` e `brotli` aos grupos `deploy` e `editor` no `pyproject.toml`, sincronizar o ambiente com `uv sync` e verificar que `import zstandard` e `import brotli` funcionam no ambiente do projeto

## 2. Query Overpass com 3 Bounding Boxes Disjuntas e Compressão em Streaming

- [x] 2.1 Escrever testes em `scripts/gerar_malha_estrada_lib_test.py` validando: (a) `construir_query_overpass` com 3 Bounding Boxes disjuntas (`4 km` incluindo `unclassified`, `60 km` para `tertiary|tertiary_link` e `180 km` para `motorway..secondary_link`) e `out body qt; >; out skel qt;`; (b) envio de `Accept-Encoding: zstd, br, gzip, deflate` e descompressão em streaming para `zstd`, `br`, `gzip`, `deflate` e `identity`; e (c) chamada best-effort a `/api/kill_my_queries` ao cancelar durante o streaming ou sofrer timeout (Red)
- [x] 2.2 Implementar `_calcular_bbox_graus`, `construir_query_overpass`, descompressão incremental por `Content-Encoding` e `_encerrar_queries_pendentes_espelho` em `scripts/gerar_malha_estrada_lib.py` (atualizando também `ESPELHOS_OVERPASS_PADRAO` para substituir `maps.mail.ru` por `lz4.overpass-api.de`) e verificar 100% de cobertura em `scripts/gerar_malha_estrada_lib.py` (Green)

## 3. Atualização *In-Place* da Linha de Download no `DialogoProgressoMalhaEstrada` e Validação de `duracao_minutos`

- [x] 3.1 Escrever teste de widget em `editor/views/widget_mensagem_coordenada_test.py` verificando que múltiplas mensagens consecutivas de `"Recebendo malha viária de ..."` atualizam a mesma linha no `QPlainTextEdit` (`lista_etapas`) sem criar linhas duplicadas, mantendo as etapas anteriores e posteriores intactas (Red)
- [x] 3.2 Implementar a atualização *in-place* da linha de recebimento em `DialogoProgressoMalhaEstrada._ao_progresso` em `editor/views/widget_mensagem_coordenada.py` e validar com `pytest` (Green)
- [x] 3.3 Escrever testes e implementar a validação de `duracao_minutos > 0` (para nós com `distancia_metros > 0`) em `malha_estrada_pico_atualizada`, `_pico_possui_malha_estrada_atualizada` e `WidgetMensagemCoordenada._atualizar_status_malha_pico` (Red -> Green)
