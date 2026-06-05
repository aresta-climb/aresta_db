## 1. Renomeação do Adapter e Testes

- [x] 1.1 Renomear `editor/core/protobuf_tree_model.py` para `editor/views/tree_view_adapter.py`.
- [x] 1.2 Renomear `ProtobufTreeModel` para `ProtobufTreeViewAdapter` e `rebuild_tree` para `inicializar_arvore` no arquivo.
- [x] 1.3 Renomear `editor/core/protobuf_tree_model_test.py` para `editor/views/tree_view_adapter_test.py` (ou mover e renomear) e atualizar as referências internas aos novos nomes.
- [x] 1.4 Atualizar `widget_editor_dados.py` para importar o novo `ProtobufTreeViewAdapter` e usar `inicializar_arvore()` no `__init__`.

## 2. Refatoração do WidgetFormularioPadrao

- [x] 2.1 Mudar herança de `WidgetFormularioPadrao` para `QStackedWidget`.
- [x] 2.2 Criar um dicionário `self.cached_forms = {}` (mapeando `msg_id` para `QScrollArea`).
- [x] 2.3 Refatorar método `load_node`: checar o cache e apenas chamar `setCurrentWidget(form)` se ele já existir. Se não existir, criar o novo layout em um `QScrollArea`, salvá-lo no cache e adicioná-lo ao Stack.
- [x] 2.4 Remover completamente o sinal customizado que forçava um `layoutChanged.emit()` no tree_model a cada caractere alterado.

## 3. Limpeza do WidgetEditorDados

- [x] 3.1 Remover chamadas à `inicializar_arvore` nos métodos modificadores `_executar_adicionar_item`, `_executar_remover_item`, `_executar_mover_para_cima` e `_executar_mover_para_baixo`.
- [x] 3.2 Garantir que o `ProtobufTreeViewAdapter` emite e captura perfeitamente os eventos `beginInsertRows`, `beginRemoveRows` e `dataChanged` para evitar bugs visuais ou expansões aleatórias na View.

## 4. Validação

- [x] 4.1 Rodar a suíte de testes de `widget_editor_dados_test.py` e resolver eventuais falhas causadas pela renomeação do tree model ou por ausência do `rebuild_tree`.
- [x] 4.2 Executar testes visuais abrindo o `main.py`, editando valores, inserindo itens, apagando itens, e voltando entre nós diferentes da árvore para garantir que o cache mantém o estado.
