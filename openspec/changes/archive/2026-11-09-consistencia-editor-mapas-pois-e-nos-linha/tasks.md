# Tasks

## 1. Schema Protobuf (`aresta_api`) e Biblioteca Pura de Geometrias (`editor/core/geometrias_poi.py`)

- [x] 1.1 Adicionar o campo `bool preenchido = 15;` em `Mapa.PontoDeInteresse` no arquivo `aresta_api/proto/croqui.proto`, recompilar os stubs Protobuf (`croqui_pb2.py` e `croqui_pb2.pyi`) e adicionar teste de contrato em `aresta_api/src/proto_validacao_test.py` verificando serialização e leitura de `preenchido`, executando `uv run pytest aresta_api/src/proto_validacao_test.py`.
- [x] 1.2 Implementar em `editor/core/geometrias_poi.py` (via ciclo TDD em `editor/core/geometrias_poi_test.py`) a função `calcular_cor_texto_contraste(cor_hex: str, preenchido: bool) -> str` e estender `redimensionar_pois_proporcionalmente` para reescalar também `linha.espessura`, `no.raio` e `no.tamanho_fonte` nos nós de linha e marcadores compilados, validando 100% de cobertura com `uv run pytest editor/core/geometrias_poi_test.py --cov=editor.core.geometrias_poi --cov-report=term-missing`.

## 2. Diálogo de Edição (`DialogoEdicaoPOI`), Preenchimento Sólido (`preenchido`) e Preservação de Cor/Highlight em `BaseItemPOI`

- [x] 2.1 Atualizar `DialogoEdicaoPOI` em `editor/views/widget_editor_mapas.py` para incluir ícones informativos `ⓘ` com *tooltips* explicativos nos campos `ID (UID)`, `Rótulo (Codenome)` e `Texto Visível`, adicionar o checkbox `chk_preenchido` (`"Preenchimento Sólido (Opaco)"`) e permitir confirmar com `rotulo` e `texto_visivel` vazios (gerando `uid` automaticamente), validando o comportamento em `editor/views/widget_editor_mapas_test.py`.
- [x] 2.2 Atualizar `BaseItemPOI` e `WidgetEditorMapas` em `editor/views/widget_editor_mapas.py` para renderizar `preenchido=True` com `alpha=255` e contraste automático de texto, adicionar a ação `"Alternar Preenchimento (Opaco / Translúcido)"` no menu de contexto com Undo/Redo, e corrigir `hoverLeaveEvent`, `remover_destaque_pois` e `destacar_pois_temporariamente` para preservarem cores customizadas e destacarem formas opacas em Ciano, validando com `uv run pytest editor/views/widget_editor_mapas_test.py`.

## 3. Paridade de Redimensionamento em Nós de Linha (`AlcaNoTrajeto`) e Sliders Bulk

- [x] 3.1 Implementar em `AlcaNoTrajeto` (`editor/views/widget_editor_mapas.py`) o redimensionamento interativo via `Ctrl + arrastar` com registro atômico no `QUndoStack` ao soltar o mouse, e atualizar `obter_raio()`, `atualizar_estilo()` e `paint()` para que todos os tipos semânticos de nó (`PROTECAO_FIXA`, `PARADA_INTERMEDIARIA`, `TOP_PARADA`, `CRUX`, `PROTECAO_MOVEL`, `PROTECAO_PITON`, `PROTECAO_FITA`, `BURACO_CLIFF`, `SETA_DIRECIONAL`) escalem proporcionalmente a `no.raio`, validando com testes comportamentais em `editor/views/widget_editor_mapas_test.py`.
- [x] 3.2 Adicionar no painel esquerdo de `WidgetEditorMapas` os novos sliders bulk `Nós de Linha:` e `Espessura Linhas:` (`-50%` a `+50%`) com suporte a `CmdMacro`, e corrigir os sliders existentes de `Retângulos` e `Quadrados` (atualização de posição/fonte em tempo real durante `ao_mover_slider_bulk`, reset de `slider_quad` em `ao_soltar_slider_bulk` e `mesmo_tipo = True` para `ItemBoundingQuadrado` em `_on_repeated_item_alterado`), validando com `uv run pytest editor/views/widget_editor_mapas_test.py`.

## 4. Criação no Ponto Clicado, Auto-Vinculação, Memória de Estilo e Duplicação de POIs

- [x] 4.1 Implementar em `WidgetEditorMapas` e `VisualizadorMapa` (`editor/views/widget_editor_mapas.py`) a memória de estilo na sessão (`_ultimo_estilo_poi`), a auto-vinculação automática de novos POIs à `Referencia` selecionada/ativa, a ação `"Duplicar Elemento"` no menu de contexto de `BaseItemPOI` e o menu de contexto no fundo vazio do mapa (`"Adicionar Círculo Aqui..."`, `"Adicionar Ponto Opaco Aqui"`, `"Adicionar Retângulo Aqui..."`, `"Iniciar Nova Rota Aqui..."`), validando todos os fluxos e Undo/Redo com `uv run pytest editor/views/widget_editor_mapas_test.py`.
