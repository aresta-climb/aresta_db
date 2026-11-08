# Tasks

## 1. Biblioteca Pura de Reajuste Proporcional de POIs (`editor/core/geometrias_poi.py`)

- [x] 1.1 Escrever testes comportamentais (Red) em `editor/core/geometrias_poi_test.py` para `redimensionar_pois_proporcionalmente` cobrindo as 5 geometrias (`circulo`, `quadrado`, `retangulo`, `poligono` e `linha.conteudo.nos`), casos de mesma resolução e dimensões inválidas/zero, e verificar que falham antes da implementação
- [x] 1.2 Implementar `redimensionar_pois_proporcionalmente` em `editor/core/geometrias_poi.py` e verificar aprovação de 100% dos testes e cobertura em `uv run pytest editor/core/geometrias_poi_test.py --cov=editor.core.geometrias_poi --cov-report=term-missing`

## 2. Substituição Atômica de Imagem de Mapa nos Controladores (`CroquiController` e `MapasController`)

- [x] 2.1 Escrever testes comportamentais (Red) em `editor/controllers/croqui_controller_test.py` e `editor/controllers/mapas_controller_test.py` para `substituir_imagem_mapa` (com e sem mudança de resolução, com e sem reajuste proporcional de POIs, e verificação de reversão completa em um único `Undo` na `QUndoStack`)
- [x] 2.2 Implementar `substituir_imagem_mapa` em `editor/controllers/croqui_controller.py` e `editor/controllers/mapas_controller.py` usando exclusivamente `CmdMacro`, `CmdAlterarImagem` e `CmdAlterarCampo`, e verificar 100% de cobertura nos testes dos controladores com `uv run pytest editor/controllers/croqui_controller_test.py editor/controllers/mapas_controller_test.py`

## 3. Unificação do Wizard de 2 Abas com Recorte Interativo (`DialogoAdicionarMapa` e `DialogoInserirImagemMarkdown`)

- [x] 3.1 Escrever testes comportamentais (Red) em `editor/views/dialogos/dialogo_adicionar_mapa_test.py` e `editor/views/dialogos/dialogo_inserir_imagem_markdown_test.py` cobrindo: aba `"Imagens do Croqui"` (busca, seleção de imagem do disco e da RAM) no `DialogoAdicionarMapa`; modo de destino fixo (`caminho_destino_fixo`); modo de substituição de mapa com checkbox `chk_reescalar_pois` dinâmico conforme mudança de resolução; e barra de recorte interativo (`✂ Recortar Área Selecionada` e `↺ Reverter Imagem Original`) no `DialogoInserirImagemMarkdown`
- [x] 3.2 Implementar a unificação das 2 abas (`"Importar Nova Imagem"` com recorte + `"Imagens do Croqui"`), modo de substituição/destino fixo e opção de reajuste proporcional de POIs em `editor/views/dialogos/dialogo_adicionar_mapa.py` e `editor/views/dialogos/dialogo_inserir_imagem_markdown.py`, verificando aprovação e cobertura com `uv run pytest editor/views/dialogos/dialogo_adicionar_mapa_test.py editor/views/dialogos/dialogo_inserir_imagem_markdown_test.py`

## 4. Botão `"Substituir Imagem..."` no Editor de Dados e Atualização do Editor de Mapas

- [x] 4.1 Escrever testes comportamentais (Red) em `editor/views/componentes/widget_card_mapa_test.py`, `editor/views/widget_editor_dados_test.py` e `editor/views/widget_editor_mapas_test.py` para o botão `"Substituir Imagem..."` no `WidgetCardMapa`, na visão de nó `MAPA` do `WidgetEditorDados` e no `WidgetEditorMapas` acionando o wizard unificado e atualizando imagem, resolução e POIs via histórico
- [x] 4.2 Implementar o botão e sinal de substituição em `editor/views/componentes/widget_card_mapa.py`, `editor/views/protobuf_widget_factory.py`, `editor/views/widget_editor_dados.py` e `editor/views/widget_editor_mapas.py`, verificando aprovação dos testes com `uv run pytest editor/views/componentes/widget_card_mapa_test.py editor/views/widget_editor_dados_test.py editor/views/widget_editor_mapas_test.py`

## 5. Unificação de `WidgetCampoImagem` e `WidgetEditorImagens` e Correção de Pureza MVC

- [x] 5.1 Escrever testes comportamentais (Red) em `editor/views/widget_campo_imagem_test.py` e `editor/legacy_views/widget_editor_imagens_test.py` validando a abertura do wizard unificado de 2 abas, a ausência de mutação direta da View sobre `CroquiModel` em `WidgetCampoImagem.aplicar_nova_imagem` e a reversão de `bytes_antigos` via `Undo` em campos de nome fixo (`thumbnail.webp`)
- [x] 5.2 Atualizar `editor/views/widget_campo_imagem.py` (removendo `DialogoNomeImagem` e a chamada direta a `definir_imagem_memoria` na View) e `editor/legacy_views/widget_editor_imagens.py` para usar o wizard unificado, atualizando `editor/views/README.md` e verificando aprovação com `uv run pytest editor/views/widget_campo_imagem_test.py editor/legacy_views/widget_editor_imagens_test.py`

## 6. Verificação de Conformidade Arquitetural e Regressão Global

- [x] 6.1 Executar o teste estático de arquitetura MVC (`uv run pytest editor/arquitetura_mvc_test.py`) e a suíte completa de testes afetados para confirmar zero violações de comandos canônicos, zero mocks internos e 100% de cobertura nos módulos modificados
