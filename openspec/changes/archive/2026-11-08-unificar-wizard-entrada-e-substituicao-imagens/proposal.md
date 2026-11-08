# Proposal

## Why

Atualmente, os fluxos de entrada e substituição de imagens no Editor Aresta estão fragmentados e inconsistentes: apenas a criação de novos mapas (`DialogoAdicionarMapa`) oferece Drag & Drop, pré-visualização, recorte interativo (*rubber-band crop*) e metadados ricos, enquanto o Editor de Mapas (`WidgetEditorMapas`), o Editor de Imagens (`WidgetEditorImagens`) e os campos de imagem (`WidgetCampoImagem` para thumbnail e fotos de capa) ainda usam seletores de arquivo crus (`QFileDialog` / `DialogoNomeImagem`), não permitem escolher imagens existentes da galeria do croqui em todos os fluxos, não oferecem botão de substituição nos cartões de mapas do Editor de Dados (`WidgetCardMapa` e nó `MAPA`), e não atualizam a resolução do mapa nem reajustam proporcionalmente os Pontos de Interesse (POIs) quando a imagem substituída muda de dimensões.

## What Changes

- **Wizard Unificado de Entrada e Substituição de Imagens (2 Abas em Todos os Fluxos)**: Unificar `DialogoAdicionarMapa` e `DialogoInserirImagemMarkdown` (e aposentar `DialogoNomeImagem`) em uma arquitetura compartilhada com duas abas disponíveis em qualquer ponto de entrada ou substituição de imagem:
  - **Aba "Importar Nova Imagem"**: seleção por botão, área de Drag & Drop com preview (`AreaDropImagem`), barra de recorte interativo (*rubber-band crop* com `✂ Recortar Área Selecionada` e `↺ Reverter Imagem Original`, inclusive no fluxo de Markdown e campos de capa/thumbnail), painel de metadados ricos ($W \times H\text{ px}$, tamanho WebP vs. original), orçamento de área contextual ($4.0\text{ MP}$ padrão vs. $1.0\text{ MP}$ para escaladas e capas) e suporte tanto a **Modo Adição / Nome Livre** (com validação de colisão em RAM e disco) quanto a **Modo Substituição / Destino Fixo** (`caminho_destino_fixo`, sem falso alerta de colisão consigo mesmo).
  - **Aba "Imagens do Croqui" (Galeria)**: busca textual instantânea e grade de miniaturas listando todas as imagens existentes na pasta `imagens/` do disco e no buffer em memória RAM (`CroquiModel`), exibindo metadados da imagem selecionada e permitindo reutilizar ou substituir a partir de imagens já presentes no croqui em qualquer fluxo.
- **Botão `"Substituir Imagem..."` no Editor de Dados**: Adicionar o botão `"Substituir Imagem..."` diretamente no `WidgetCardMapa` (ao lado de `"Abrir no Editor de Mapas"`) e na visualização de nó `MAPA` da árvore do `WidgetEditorDados`, permitindo substituir a imagem de um mapa sem precisar removê-lo ou sair do Editor de Dados.
- **Atualização Atômica de Dimensões do Mapa e Reajuste Proporcional de POIs (`Library-First`)**:
  - Adicionar na biblioteca pura `editor/core/geometrias_poi.py` a função `redimensionar_pois_proporcionalmente(pontos_de_interesse, largura_antiga, altura_antiga, largura_nova, altura_nova)` para reescalar coordenadas e dimensões de todas as geometrias de POI (`circulo`, `quadrado`, `retangulo`, `poligono` e `linha.conteudo.nos`).
  - No wizard de substituição de imagem de mapa, quando o mapa possuir POIs cadastrados e a nova resolução ($W_{\text{novo}} \times H_{\text{novo}}$) diferir da resolução anterior ($W_{\text{antigo}} \times H_{\text{antigo}}$), exibir a opção (marcada por padrão) para reajustar proporcionalmente os POIs.
  - Orquestrar a substituição no `CroquiController` e `MapasController` via um único `CmdMacro` canônico agrupando `CmdAlterarImagem` e `CmdAlterarCampo` (para `caminho_imagem_mapa`, `largura_mapa`, `altura_mapa` e `pontos_de_interesse.<idx>`), garantindo reversão integral em um único `Undo`.
- **Modernização de `WidgetCampoImagem`, `WidgetEditorMapas` e `WidgetEditorImagens`**:
  - Substituir o `QFileDialog` cru nos botões `"Substituir Imagem..."` do `WidgetEditorMapas` e `WidgetEditorImagens` e no botão `"Trocar Imagem..."` do `WidgetCampoImagem` pelo wizard unificado.
  - Remover a mutação direta `self.model.definir_imagem_memoria` de dentro da View `WidgetCampoImagem`, delegando 100% da mutação ao `CroquiController.alterar_campo_imagem` e preservando `bytes_antigos` para Undo/Redo em campos de nome fixo (`thumbnail.webp`).

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability isolada necessária; as capacidades existentes cobrem os módulos afetados. -->

### Modified Capabilities
- `editor-dados-mapa-gateway`: Adiciona o botão `"Substituir Imagem..."` em `WidgetCardMapa` e na visão de nó `MAPA` do Editor de Dados, além da aba `"Imagens do Croqui"` no diálogo de adição/substituição de mapas.
- `editor-mapas`: Atualiza a substituição de imagem do mapa para utilizar o wizard unificado de 2 abas (com recorte e galeria), atualizar `largura_mapa` e `altura_mapa` e oferecer reajuste proporcional atômico dos POIs via `CmdMacro`.
- `editor-imagens`: Atualiza a ação `"Substituir Imagem..."` do `WidgetEditorImagens` para abrir o wizard unificado (com Drag & Drop, preview, recorte e galeria) em modo de destino fixo.
- `editor-campo-imagem`: Atualiza `WidgetCampoImagem` (`caminho_thumbnail` e `caminho_imagem_capa`) para utilizar o wizard unificado de 2 abas com recorte, aposenta `DialogoNomeImagem` e corrige a pureza MVC para preservar `bytes_antigos` no histórico.
- `editor-markdown-imagens`: Incorpora a barra de recorte interativo (*rubber-band crop* e reversão de corte) na aba `"Importar Nova Imagem"` do `DialogoInserirImagemMarkdown` através da base unificada do wizard.

## Impact

- **Biblioteca Core (`editor/core/`)**:
  - `editor/core/geometrias_poi.py` e `editor/core/geometrias_poi_test.py`: nova função pura `redimensionar_pois_proporcionalmente`.
- **Controladores (`editor/controllers/`)**:
  - `editor/controllers/croqui_controller.py`, `editor/controllers/mapas_controller.py` e respectivos testes: método `substituir_imagem_mapa` agrupando `CmdAlterarImagem` e `CmdAlterarCampo` (dimensões e POIs reescalados) em `CmdMacro`.
- **Diálogos e Componentes de UI (`editor/views/` e `editor/legacy_views/`)**:
  - `editor/views/dialogos/dialogo_adicionar_mapa.py` e `editor/views/dialogos/dialogo_inserir_imagem_markdown.py`: consolidação da estrutura de 2 abas (`Importar Nova Imagem` com recorte + `Imagens do Croqui`), modo de destino fixo e opção de reajuste proporcional de POIs.
  - `editor/views/componentes/widget_card_mapa.py`: novo botão `"Substituir Imagem..."` conectado ao fluxo unificado.
  - `editor/views/widget_editor_dados.py`: botão `"Substituir Imagem..."` na visão de nó `MAPA`.
  - `editor/views/widget_campo_imagem.py`: uso do wizard unificado, remoção de `DialogoNomeImagem` e remoção da mutação direta na View.
  - `editor/views/widget_editor_mapas.py` e `editor/legacy_views/widget_editor_imagens.py`: substituição de `QFileDialog` pelo wizard unificado.
