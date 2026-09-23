## 1. Criação do Componente Visual WidgetCardMapa

- [x] 1.1 Criar suite de testes unitários `editor/views/componentes/widget_card_mapa_test.py` cobrindo inicialização, exibição da miniatura, metadados de resolução, fallback de imagem ausente, clique em "Abrir no Editor de Mapas" e método `definir_indice()`.
- [x] 1.2 Implementar a classe `WidgetCardMapa` em `editor/views/componentes/widget_card_mapa.py` contendo cabeçalho com alça `⠿`, índice e nome do arquivo, botões de ação (▲, ▼, Remover), miniatura proporcional, caminho, resolução e botão para o Editor de Mapas.

## 2. Integração no ContainerRepeatedWidget

- [x] 2.1 Atualizar `ContainerRepeatedWidget._renderizar_item_no_indice` em `editor/views/widget_editor_dados.py` para detectar mensagens de `Mapa` (`mensagem_formato_na_ui == MAPA`) e instanciar `WidgetCardMapa` em vez de `WidgetColapsavel`.
- [x] 2.2 Conectar os botões `▲`, `▼` e `Remover` do `WidgetCardMapa` aos métodos do `CroquiController` (`mover_repeated_para_cima`, `mover_repeated_para_baixo`, `remover_repeated`) com consolidação preventiva de edições pendentes.
- [x] 2.3 Atualizar `_atualizar_indices_e_botoes()` em `ContainerRepeatedWidget` para atualizar os índices e botões de `WidgetCardMapa` quando a lista for reordenada ou itens forem adicionados/removidos.
- [x] 2.4 Integrar o arraste de `WidgetCardMapa` com o sistema de drag-and-drop (`_iniciar_drag`, linha indicadora e `dropEvent`).

## 3. Testes de Integração e Verificação

- [x] 3.1 Adicionar testes de integração em `editor/views/widget_editor_dados_test.py` cobrindo a renderização de mapas como `WidgetCardMapa` (sem accordion colapsável), exibição da miniatura e navegação ao clicar no botão "Abrir no Editor de Mapas".
- [x] 3.2 Adicionar testes em `editor/views/widget_editor_dados_test.py` cobrindo a reordenação de `WidgetCardMapa` via botões ▲/▼ e via drag-and-drop, validando reversibilidade com Undo (`Ctrl+Z`) e Redo (`Ctrl+Y`).
- [x] 3.3 Executar a suíte de testes do editor (`pytest editor/ -m "not slow"`) para assegurar 100% de aprovação e ausência de regressões.
