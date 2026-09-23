# Proposta: Reordenação de Listas no Editor de Dados

## Why

Atualmente, coleções repetidas renderizadas no formulário do editor de dados (`ContainerRepeatedWidget`), como escaladas em um setor, vias, sinônimos, variantes ou pontos de interesse de um mapa, apenas permitem adicionar novos itens ou remover itens existentes. Não há como reordenar itens para ajustar a sequência das escaladas de uma falésia, reorganizar paradas de uma via ou priorizar dados, limitando a usabilidade e forçando remoções e recriações manuais.

## What Changes

- **Botões de Reordenação Rápida (▲ / ▼)**: Adicionar botões "Subir" e "Descer" em cada item da lista (primitivos ou mensagens colapsáveis), desabilitando adequadamente nos limites (primeiro item não pode subir, último não pode descer).
- **Alça de Arraste (Drag Handle `⠿`) e Drag and Drop**: Adicionar alça visual de arraste em cada item permitindo reordenar itens arrastando e soltando diretamente dentro do container da lista.
- **Indicador Visual de Inserção**: Exibir uma linha indicadora visual de inserção durante o arraste indicando a posição de soltura entre os itens.
- **Sincronização de Estado e Numeração**: Conectar o sinal do modelo `repeated_movido` para reorganizar os widgets no layout, atualizar os títulos indexados (ex: `Escalada [0]`, `Escalada [1]`) e os estados habilitado/desabilitado dos botões de movimentação.
- **Integração com Histórico Undo/Redo**: Toda movimentação (seja via botões ou drag-and-drop) despachará o comando atômico `CmdMoverRepeated` no histórico (`QUndoStack`), garantindo reversibilidade total via `Ctrl+Z` e `Ctrl+Y`.

## Capabilities

### Modified Capabilities

- `editor-dados-formularios`: Adiciona suporte a reordenação de itens em coleções repetidas através de botões de movimentação e interação de arrastar e soltar (drag-and-drop).

## Impact

- `editor/views/widget_editor_dados.py`: Atualizações em `ContainerRepeatedWidget` e `WidgetColapsavel` para incluir a alça de arraste, botões de ação e tratamento de eventos de mouse e drag-and-drop.
- `editor/views/widget_editor_dados_test.py`: Novos testes unitários e de integração validando a movimentação, reindexação e desfecho via Undo/Redo.
