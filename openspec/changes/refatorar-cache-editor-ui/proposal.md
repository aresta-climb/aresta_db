## Why

O `WidgetEditorDados` reconstrói toda a árvore visual (`QTreeView`) e todos os formulários sempre que o modelo interno sofre mutação ou quando o usuário seleciona itens, perdendo o estado do scroll, dos campos de texto e a expansão da árvore. A refatoração atualiza a interface para reutilizar componentes existentes utilizando Cache (QStackedWidget) e responder de maneira reativa apenas aos campos alterados através dos sinais otimizados do `ProtobufTreeModel` e `QAbstractItemModel`, eliminando a fragilidade estrutural da tela. 

## What Changes

- Refatoração do `WidgetFormularioPadrao` para herdar/utilizar `QStackedWidget` ao invés de forçar resets do container raiz, cacheando `QScrollArea`s para cada formulário já instanciado baseado na referência/ID da mensagem em edição.
- Remoção de todos os gatilhos destruidores (`rebuild_tree` e `layoutChanged`) das rotinas de edição e reordenamento do `WidgetEditorDados` e `WidgetFormularioPadrao`.
- Aproveitamento exclusivo das notificações granulares já suportadas pelo model (`dataChanged`, `beginInsertRows`, `beginRemoveRows`) que garantem animações limpas e estabilidade de estado e layout.
- Renomeação da classe `ProtobufTreeModel` para `ProtobufTreeViewAdapter` e do método `rebuild_tree` para `inicializar_arvore`, evitando ambiguidades entre models de negócio e adaptadores de exibição Qt.

## Capabilities

### New Capabilities
*(Não há novas capacidades de negócio sendo introduzidas. Trata-se de refatoração estritamente arquitetural e visual de estabilidade)*

### Modified Capabilities
- `editor-dados`: Ajustes de eficiência de renderização e correção de interrupções de fluxo de trabalho do usuário na interface de edição, mantendo o estado entre trocas de visualização de nós.

## Impact

- `editor.views.widget_editor_dados` (arquitetura do WidgetFormularioPadrao e gatilhos de atualização).
- `editor.core.protobuf_tree_model` (será movido/renomeado para `editor.views.tree_view_adapter.py`).
- Testes envolvidos (`widget_editor_dados_test.py`, `protobuf_tree_model_test.py`).
