# Proposal

## Why

O Editor de Mapas possui assimetrias de usabilidade e lacunas funcionais entre POIs avulsos (`circulo`, `retangulo`, `quadrado`, `poligono`) e nós de linhas (`AlcaNoTrajeto` em `ItemTrajetoLinha`), além de limitações que dificultam fluxos comuns de mapeamento — como desenhar marcadores circulares opacos (preenchidos) sem texto na base da parede e vinculá-los a uma referência para receberem *highlight* conjunto com a caixa numerada da via, redimensionar nós de linhas com `Ctrl + arrastar` ou via sliders em lote, criar elementos diretamente no ponto clicado com auto-vinculação à referência selecionada, e compreender a diferença entre `rotulo` (codenome lógico da referência) e `texto_visivel` (texto desenhado sobre o mapa) nos diálogos de edição. Também foram identificados bugs visuais em que o *hover* e a remoção de destaque sobrescrevem cores customizadas para verde fixo e sliders em lote não atualizam o texto nem resetam corretamente para quadrados.

## What Changes

- **Preenchimento Sólido (`preenchido`) em POIs e Contraste Automático**:
  - Adicionar o campo `bool preenchido = 15;` em `Mapa.PontoDeInteresse` (`aresta_api/proto/croqui.proto`).
  - Quando `preenchido = true`, renderizar formas (`circulo`, `retangulo`, `quadrado`, `poligono`) com opacidade sólida (`alpha = 255`) na cor do elemento (ex.: círculo preto sólido `#000000`) e ajustar automaticamente o contraste da fonte de `texto_visivel` (branco sobre fundos escuros, preto sobre fundos claros).
  - Adicionar checkbox `"Preenchimento Sólido (Opaco)"` no `DialogoEdicaoPOI` e ação `"Alternar Preenchimento (Opaco / Translúcido)"` no menu de contexto de POIs, com suporte a Undo/Redo.
- **POIs Sem Rótulo/Texto e Ícones Explicativos `ⓘ` no Wizard (`DialogoEdicaoPOI`)**:
  - Permitir confirmar a criação/edição de POIs no `DialogoEdicaoPOI` mesmo com `rotulo` e `texto_visivel` em branco, gerando `uid` automaticamente quando omitido (ideal para marcadores/bolinhas mudas vinculadas a uma referência).
  - Renomear os rótulos dos campos no `DialogoEdicaoPOI` e adicionar ícones informativos **`ⓘ`** com *tooltips* detalhando a diferença entre `ID (UID)`, `Rótulo (Codenome da Referência)` e `Texto Visível (Desenhado no Mapa)`.
- **Preservação de Cor/Preenchimento no Hover e Highlight de Referências**:
  - Corrigir `BaseItemPOI.hoverLeaveEvent` e `WidgetEditorMapas.remover_destaque_pois` para restaurarem o estilo real do POI via `atualizar_estilo_visual()` em vez de sobrescreverem com verde fixo `QColor(0, 255, 0, 50)`.
  - Garantir que POIs opacos (`preenchido = true`, com ou sem texto) recebam *highlight* Ciano de alto contraste quando sua `Referencia` vinculada for selecionada, estiver em modo vinculação ou receber *hover*.
- **Paridade de Redimensionamento e Escala em Nós de Linha (`AlcaNoTrajeto` e `ItemTrajetoLinha`)**:
  - Suportar `Ctrl + arrastar` diretamente sobre qualquer `AlcaNoTrajeto` para redimensionar `no.raio` interativamente em tempo real (com escala automática da fonte quando `no.tamanho_fonte == 0`) e registrar um único comando de Undo/Redo ao soltar o mouse.
  - Fazer todos os tipos de marcador de `AlcaNoTrajeto` (`PROTECAO_FIXA`, `PARADA_INTERMEDIARIA`, `TOP_PARADA`, `CRUX`, `PROTECAO_MOVEL`, `PROTECAO_PITON`, `PROTECAO_FITA`, `BURACO_CLIFF`, `SETA_DIRECIONAL`), e não apenas os tipos `1`, `2` e `11`, escalarem seu desenho e `boundingRect` proporcionalmente a `no.raio`.
  - Adicionar novos sliders de redimensionamento em lote (*bulk*) no painel esquerdo para **`Nós de Linha:` (`-50%` a `+50%`)** e **`Espessura Linhas:` (`-50%` a `+50%`)**, com registro em `CmdMacro` no histórico.
  - Atualizar `redimensionar_pois_proporcionalmente` (`editor/core/geometrias_poi.py`) para também reescalar `no.raio`, `no.tamanho_fonte` e `linha.espessura` quando a imagem de fundo do mapa mudar de resolução.
- **Fluxo Rápido de Criação no Ponto Clicado, Auto-Vinculação, Memória de Estilo e Duplicação**:
  - Adicionar menu de contexto no fundo vazio do mapa (botão direito na cena) com ações para criar elementos diretamente na coordenada clicada: `"Adicionar Círculo Aqui..."`, `"Adicionar Ponto Opaco Aqui"`, `"Adicionar Retângulo Aqui..."` e `"Iniciar Nova Rota Aqui..."`.
  - Auto-vincular automaticamente o novo POI criado à `Referencia` atualmente selecionada (ou em modo de vinculação) no `PainelReferencias` dentro do mesmo macro de Undo/Redo.
  - Memorizar na sessão as últimas dimensões, cor, preenchimento e tamanho de fonte utilizados ao criar POIs e adicionar a ação `"Duplicar Elemento"` no menu de contexto de POIs existentes.
- **Correções de Consistência nos Sliders Bulk e `ItemBoundingQuadrado`**:
  - Atualizar posição e tamanho da fonte em tempo real durante o movimento dos sliders bulk de `Retângulos` e `Quadrados`.
  - Resetar o slider e o rótulo percentual de `Quadrados` para `0%` ao soltar o slider em `ao_soltar_slider_bulk`.
  - Definir `mesmo_tipo = True` no ramo de `ItemBoundingQuadrado` em `_on_repeated_item_alterado` para evitar destruição e recriação desnecessária do item na cena.

## Capabilities

### New Capabilities

### Modified Capabilities
- `editor-mapas`: Adição do campo `preenchido` em POIs com contraste automático de texto e highlight fiel; permissão de POIs sem rótulo/texto e ícones explicativos `ⓘ` em `DialogoEdicaoPOI`; redimensionamento `Ctrl + arrastar` e escala por `raio` para todos os tipos de nós de linha; sliders bulk para nós de linha e espessura de linhas; reajuste proporcional de `no.raio` e `linha.espessura`; criação de POIs na coordenada clicada com auto-vinculação à referência selecionada, memória de estilo e duplicação; correção de bugs visuais em hover/highlight e sliders bulk.

## Impact

- **Schema Protobuf (`aresta_api`)**:
  - `aresta_api/proto/croqui.proto` (campo `bool preenchido = 15` em `Mapa.PontoDeInteresse`) e recompilação de `croqui_pb2.py` / `croqui_pb2.pyi`.
- **Core / Lógica Pura (`editor/core`)**:
  - `editor/core/geometrias_poi.py` e `editor/core/geometrias_poi_test.py` (reescalonamento de `linha.espessura`, `no.raio` e `no.tamanho_fonte`, cálculo de contraste de cor para fundo opaco).
- **Views (`editor/views`)**:
  - `editor/views/widget_editor_mapas.py` e `editor/views/widget_editor_mapas_test.py` (`DialogoEdicaoPOI`, `BaseItemPOI`, `AlcaNoTrajeto`, `ItemTrajetoLinha`, menus de contexto, sliders bulk, highlight e criação posicionada com auto-vinculação).
