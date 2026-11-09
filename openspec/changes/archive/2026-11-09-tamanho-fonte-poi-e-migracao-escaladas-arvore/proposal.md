# Proposal

## Why

Atualmente no Editor Aresta existem duas limitações importantes de usabilidade:
1. **Tamanho de fonte fixo em POIs avulsos no Editor de Mapas**: Ao adicionar ou editar um Ponto de Interesse (`circulo`, `retangulo`, `quadrado` ou `poligono`) com `texto_visivel` preenchido (por exemplo, para numerar uma referência nova não presente na imagem original da rocha), o texto é renderizado com fonte `Arial 12pt Bold` estática (`hardcoded`), sem escalar proporcionalmente ao redimensionar a forma geométrica (`Ctrl + arrastar`) e sem oferecer controle manual de `tamanho_fonte` (diferentemente dos círculos identificadores em `NoTrajeto` das rotas).
2. **Arrastar e soltar (Drag-and-Drop) de Escaladas entre Setores na Árvore de Dados**: Embora o controlador (`CroquiController.migrar_escalada`) e o servidor MCP (`aresta_migrar_escalada`) já suportem a migração atômica de uma `Escalada` entre setores distintos preservando UID e histórico Undo/Redo, a interface da árvore (`WidgetEditorDados._executar_soltura_arvore` e `migracao_setor.py`) bloqueia qualquer migração entre listas cujo elemento de origem não seja um `setor`, fazendo com que arrastar uma via de um setor para outro não execute nenhuma ação.

## What Changes

- **Schema Protobuf (`aresta_api/proto/croqui.proto` e stubs gerados)**:
  - Adição do campo `int32 tamanho_fonte = 14 [(aresta.texto_na_ui) = "Tamanho da Fonte"]` na mensagem `Mapa.PontoDeInteresse` (quando omitido ou `0`, utiliza cálculo automático proporcional à geometria; quando `> 0`, aplica o tamanho manual em pontos/pixels).
- **Editor de Mapas (`editor/views/widget_editor_mapas.py` e `editor/core/geometrias_poi.py`)**:
  - Implementação do cálculo automático proporcional de tamanho de fonte em `BaseItemPOI` (baseado nas dimensões de `circulo`, `retangulo`, `quadrado` ou `poligono` e no comprimento de `texto_visivel`) sempre que `tamanho_fonte` não estiver definido (`0`), atualizando dinamicamente a fonte ao redimensionar o POI com `Ctrl + arrastar` (incluindo correção em `ItemBoundingQuadrado` para reposicionar e reescalar o texto durante o redimensionamento).
  - Suporte completo à configuração manual de `tamanho_fonte` em `BaseItemPOI`: opção `"Tamanho da Fonte (Xpt)..."` no menu de contexto de todos os POIs e campo opcional de tamanho de fonte em `DialogoEdicaoPOI`, com registro reversível na pilha `QUndoStack`.
  - Reajuste proporcional de `tamanho_fonte` (em `PontoDeInteresse` e em `NoTrajeto`) na função pura `redimensionar_pois_proporcionalmente` quando a resolução da imagem do mapa for substituída.
- **Árvore de Dados (`editor/core/migracao_setor.py`, `editor/views/tree_view_adapter.py` e `editor/views/widget_editor_dados.py`)**:
  - Atualização de `validar_movimento_permitido` e `ProtobufTreeViewAdapter.flags` para permitir soltar uma `Escalada` entre escaladas de outro setor, sobre o nó agrupador `Escaladas` (`expando`), antes do nó `+ Adicionar Escalada`, ou diretamente sobre um nó `Setor` de destino.
  - Conexão de `WidgetEditorDados._executar_soltura_arvore` ao método `CroquiController.migrar_escalada` quando `origem_tipo == "escalada"` e o setor de destino for distinto do setor de origem, expandindo o setor de destino e selecionando a escalada migrada com suporte integral a Undo/Redo.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability isolada; os requisitos estendem capacidades existentes. -->

### Modified Capabilities
- `editor-mapas`: Adiciona requisitos de dimensionamento automático (proporcional à caixa geométrica) e manual (`tamanho_fonte`) do `texto_visivel` em Pontos de Interesse (`circulo`, `retangulo`, `quadrado`, `poligono`, `linha`), via menu de contexto, diálogo de edição e redimensionamento interativo, além do reajuste proporcional de `tamanho_fonte` ao redimensionar imagens de mapas.
- `editor-dados-arvore`: Adiciona requisitos de migração de `Escalada` entre diferentes `Setor` via arrastar e soltar (drag-and-drop) na árvore de dados (soltura entre escaladas de outro setor, sobre o agrupador `Escaladas` ou sobre o próprio `Setor`), integrando com `CroquiController.migrar_escalada` e histórico Undo/Redo.

## Impact

- **Código Afetado**:
  - `aresta_api/proto/croqui.proto` e `aresta_api/proto/generated/croqui_pb2.py` (via `aresta_api/build.py`)
  - `editor/core/geometrias_poi.py` e `editor/core/geometrias_poi_test.py`
  - `editor/views/widget_editor_mapas.py` e `editor/views/widget_editor_mapas_test.py`
  - `editor/core/migracao_setor.py` e `editor/core/migracao_setor_test.py`
  - `editor/views/tree_view_adapter.py` e `editor/views/tree_view_adapter_test.py`
  - `editor/views/widget_editor_dados.py` e `editor/views/widget_editor_dados_test.py`
- **Compatibilidade**: Adição de campo opcional `int32 tamanho_fonte = 14` em `Mapa.PontoDeInteresse` é 100% retrocompatível em Protobuf/YAML.
