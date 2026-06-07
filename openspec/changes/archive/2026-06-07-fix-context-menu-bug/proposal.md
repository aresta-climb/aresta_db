## Why

Atualmente, o menu de contexto (botão direito) na árvore de dados não funciona corretamente para itens recém-adicionados (como "Setores ou Grupos" ou "Picos"). Quando o usuário tenta "Excluir item", "Mover para Cima" ou "Mover para Baixo" em um item recém-criado, a ação falha silenciosamente. Isso ocorre porque o PyQt usa um objeto volátil (`QModelIndex`) que é invalidado pelo motor de renderização durante a exibição do menu de contexto. Além disso, há um bug na auto-seleção de itens ao adicionar novos nós aninhados, que pode selecionar e apagar itens errados em nós homônimos. 

## What Changes

- Modificar a passagem de índices nos callbacks (lambdas) do menu de contexto em `WidgetEditorDados` para utilizar `QPersistentModelIndex`.
- Corrigir a heurística de busca em `_localizar_no_por_indice` e `_localizar_novo_idx` para que a busca limite seu escopo aos filhos diretos do `expando_node` afetado, em vez de fazer uma busca global a partir do nó raiz.
- Escrever testes automatizados (integração/UI) atestando que os nós corretos são selecionados e que os índices não se perdem.

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- `editor.views.widget_editor_dados.py`: Funções de menu de contexto e localização de nós.
- `editor.views.widget_editor_dados_test.py`: Adição de testes em TDD para provar o bug antes do refactor.
