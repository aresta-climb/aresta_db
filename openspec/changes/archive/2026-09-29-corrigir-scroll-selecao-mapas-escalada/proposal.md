## Why

Ao abrir um mapa individual de escalada (seja através do botão "Abrir no Editor de Mapas" na árvore de dados, seja clicando na lista de mapas), a seleção visual da barra lateral salta erroneamente para o mapa do setor pai. Consequentemente, ao pressionar a tecla para baixo (↓) para navegar pelos itens da lista, a seleção entra em um ciclo fechado nos mapas do setor, impedindo a rolagem e navegação para os mapas subsequentes e bloqueando a produtividade do editor.

## What Changes

- **Preservação do índice e tipo de escalada no Editor de Mapas**: Atualização de `set_mapa_atual`, `_on_mapa_selecionado` e `_renderizar_mapa` em `WidgetEditorMapas` para reter o índice da escalada (`e_idx`) e o tipo de mapa (`escalada_setor`, `escalada_subsetor`).
- **Casamento estrito na seleção por índices**: Aprimoramento de `selecionar_mapa_por_indices` para aceitar `e_idx` e `tipo`, garantindo que mapas de escalada correspondam unicamente aos seus nós e não colidam com mapas de setores com mesmos índices base.
- **Rolagem automática da lista (Scroll into View)**: Adição de chamada a `scrollToItem` em `list_widget` ao selecionar mapas, garantindo que a barra de rolagem acompanhe o item ativo.
- **Roteamento de foco global para mapas de escalada**: Atualização dos padrões de expressão regular e resolução de caminhos em `area_principal.py` para extrair corretamente `e_idx` e rotear o foco global de escaladas para o editor de mapas.
- **Contexto correto para histórico (Undo/Redo)**: Montagem precisa da URI de contexto em `MapasController.set_contexto` para mapas de escalada.

## Capabilities

### New Capabilities

*(Nenhuma nova capacidade introduzida)*

### Modified Capabilities

- `editor-mapas-mvc-sidebar`: Adiciona requisitos de retenção estrita de seleção de mapas de escaladas, navegação por teclado sem loops e rolagem automática na lista lateral do editor de mapas.

## Impact

- Código afetado:
  - `editor/views/widget_editor_mapas.py`: gerenciamento da lista lateral, assinaturas de seleção e renderização.
  - `editor/legacy_views/area_principal.py`: resolução e roteamento de URIs de foco de mapas de escalada.
  - `editor/views/widget_editor_mapas_test.py`: testes unitários e de integração de navegação por teclado e foco.
  - `editor/legacy_views/area_principal_test.py`: testes de navegação global.
