## Why

No editor de dados, itens repetidos de mapas (`mapas`) eram encapsulados dentro de um accordion colapsável genérico (`WidgetColapsavel`). Como o mapa não possui campos textuais de título (`nome` ou `titulo`), o accordion exibia apenas o rótulo padrão `▶ Mapas [0]`, `▶ Mapas [1]`, forçando o usuário a clicar para expandir o item apenas para encontrar um único botão ("Abrir no Editor de Mapas"), sem qualquer pré-visualização da imagem. Além de gerar cliques desnecessários, essa estrutura tornava impossível identificar visualmente as fotos das paredes ou confirmar a nova ordem das imagens ao reordenar a lista via arrastar e soltar (drag-and-drop) ou botões de subir/descer.

## What Changes

- **Substituição do Accordion por Card Aberto de Mapa**: Para coleções repetidas de mensagens do tipo `Mapa` (com anotação `mensagem_formato_na_ui = MAPA`), o container renderiza diretamente um card aberto e visual (`WidgetCardMapa`), eliminando o colapso/expansão.
- **Miniatura e Pré-visualização da Imagem**: Cada card de mapa exibe uma miniatura proporcional da imagem (`caminho_imagem_mapa`) carregada dinamicamente da memória ou do disco (`model.obter_bytes_imagem()`), com suporte a placeholder caso a imagem esteja ausente.
- **Cabeçalho de Ações e Reordenação**: O card possui em seu topo a alça de arraste `⠿` (`AlcaArrasteItem`), o identificador indexado com nome do arquivo (ex: `Mapa [0] - setor_fugitivos_p0.webp`), botões rápidos de ordenação `▲` e `▼`, e o botão `Remover`.
- **Informações e Ação Direta**: O corpo do card exibe o caminho relativo do arquivo, as dimensões em pixels da imagem (`largura_mapa × altura_mapa`) e o botão de ação destacado `Abrir no Editor de Mapas`.
- **Sincronização com Histórico**: A reordenação via botões ou drag-and-drop atualiza dinamicamente os cartões, índices e estados dos botões no layout, com suporte total e atômico a Undo (`Ctrl+Z`) e Redo (`Ctrl+Y`).

## Capabilities

### Modified Capabilities

- `editor-dados-formularios`: Adiciona especificação para renderização direta de cartões visuais para mensagens de mapa em coleções repetidas, incluindo miniatura, dados de resolução e controles de ordenação sem accordion.

## Impact

- **Código Afetado**: `editor/views/widget_editor_dados.py`, `editor/views/componentes/widget_card_mapa.py` (novo componente).
- **APIs / Modelos**: `CroquiModel` (leitura de bytes via `obter_bytes_imagem()`, escuta de `imagem_alterada`), `CroquiController` (comandos de reordenação e remoção).
- **Dependências**: Nenhuma dependência externa nova; utiliza componentes existentes do PySide6.
