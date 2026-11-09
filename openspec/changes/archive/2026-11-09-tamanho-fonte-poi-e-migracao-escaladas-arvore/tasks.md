# Tasks

## 1. Schema Protobuf e Biblioteca Pura de Geometria e Tamanho de Fonte (`geometrias_poi`)

- [x] 1.1 Adicionar o campo `int32 tamanho_fonte = 14 [(aresta.texto_na_ui) = "Tamanho da Fonte"]` em `Mapa.PontoDeInteresse` no arquivo `aresta_api/proto/croqui.proto`, recompilar os stubs via `uv run python aresta_api/build.py --force` e verificar com `uv run pytest aresta_api/` que o campo está disponível em `croqui_pb2.Mapa.PontoDeInteresse`.
- [x] 1.2 Seguindo TDD (Red-Green-Refactor), escrever testes de comportamento em `editor/core/geometrias_poi_test.py` e implementar `calcular_tamanho_fonte_poi(pt_dict)` e o reajuste proporcional de `tamanho_fonte` em `redimensionar_pois_proporcionalmente` no módulo `editor/core/geometrias_poi.py`, verificando 100% de cobertura com `uv run pytest editor/core/geometrias_poi_test.py --cov=editor.core.geometrias_poi --cov-fail-under=100`.

## 2. Tamanho de Fonte Automático e Manual no Editor de Mapas (`widget_editor_mapas`)

- [x] 2.1 Seguindo TDD, escrever testes em `editor/views/widget_editor_mapas_test.py` e atualizar `BaseItemPOI`, `ItemBoundingRetangulo`, `ItemBoundingCirculo` e `ItemBoundingQuadrado` em `editor/views/widget_editor_mapas.py` para aplicar `calcular_tamanho_fonte_poi` ao `item_texto` e recalcular dinamicamente a fonte e sua posição central durante o redimensionamento (`Ctrl + arrastar`), verificando com `uv run pytest editor/views/widget_editor_mapas_test.py`.
- [x] 2.2 Seguindo TDD, escrever testes em `editor/views/widget_editor_mapas_test.py` e adicionar o controle de `tamanho_fonte` (`0 = Automático` ou valor manual em pontos) em `DialogoEdicaoPOI` e a ação `"Tamanho da Fonte..."` no menu de contexto de `BaseItemPOI.tratar_menu_contexto` com registro reversível no `QUndoStack`, verificando com `uv run pytest editor/views/widget_editor_mapas_test.py`.

## 3. Migração de Escaladas entre Setores por Drag-and-Drop na Árvore de Dados

- [x] 3.1 Seguindo TDD, escrever testes em `editor/core/migracao_setor_test.py` e atualizar `validar_movimento_permitido` em `editor/core/migracao_setor.py` para permitir soltar `escalada` entre escaladas, antes de `+ Adicionar Escalada` (`campo_destino == "escaladas"`), sobre o agrupador `Escaladas` (`expando` com `campo_destino == "escaladas"`) ou diretamente sobre um `Setor`/`ArquivoSetor`, bloqueando destinos incompatíveis, e verificar 100% de cobertura com `uv run pytest editor/core/migracao_setor_test.py --cov=editor.core.migracao_setor --cov-fail-under=100`.
- [x] 3.2 Seguindo TDD, escrever testes em `editor/views/tree_view_adapter_test.py` e `editor/views/widget_editor_dados_test.py`, habilitar `ItemIsDropEnabled` para nós `Setor`/`ArquivoSetor` em `editor/views/tree_view_adapter.py` e conectar `ArvoreDadosTreeView.dragMoveEvent` e `WidgetEditorDados._executar_soltura_arvore` em `editor/views/widget_editor_dados.py` ao método `CroquiController.migrar_escalada` (com descarte de cache de formulário, auto-expansão do setor destino, seleção da escalada migrada e Undo/Redo), verificando com `uv run pytest editor/views/tree_view_adapter_test.py editor/views/widget_editor_dados_test.py`.
