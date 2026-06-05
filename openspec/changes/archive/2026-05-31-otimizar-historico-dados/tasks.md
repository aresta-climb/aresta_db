## 1. Barramento de Eventos e Sinais

- [x] 1.1 Modificar o `GerenciadorHistorico` (ou equivalente global de fácil acesso, como `AtualizadorUI`) para declarar os sinais PyQt: `sinal_campo_alterado`, `sinal_item_adicionado`, `sinal_item_removido`.
- [x] 1.2 Atualizar o fluxo de Undo/Redo para extrair os dados dos comandos desfeitos/refeitos (`CmdAlterarPrimitivo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`) e invocar o sinal adequado com o endereço da mensagem, nome do campo e índice/valor.

## 2. Reatividade de Widgets Primitivos

- [x] 2.1 Em `protobuf_widget_factory.py` (ou centralizado no formulário parent para evitar memory leaks), modificar a criação/configuração de widgets primitivos para reagir ao `sinal_campo_alterado`.
- [x] 2.2 Realizar a verificação da mensagem `if id(msg) == msg_id and campo == field_nome` de forma centralizada ou descentralizada.
- [x] 2.3 Implementar o bloqueio de sinais, atualização da prop da UI (`setText()`, `setValue()`, etc.) e a recuperação do foco (`setFocus()`) e seleção de texto.

## 3. Container Observador para Listas (Repeated Fields)

- [x] 3.1 Criar a classe modular `ContainerRepeatedWidget` para gerir o sub-layout de listas dinâmicas.
- [x] 3.2 Remover a injeção estática e iterativa na função `_render_repeated_field` do `WidgetFormularioPadrao` e instanciar o novo container.
- [x] 3.3 Conectar o `ContainerRepeatedWidget` aos sinais `sinal_item_adicionado` e `sinal_item_removido`.
- [x] 3.4 Implementar a resposta a `item_adicionado` construindo apenas o layout daquele item e usando `layout.insertWidget()`.
- [x] 3.5 Implementar a resposta a `item_removido` removendo o layout através do índice especificado (`layout.itemAt()`) com chamada segura de `widget.deleteLater()`.

## 4. Reatividade da Árvore de Navegação (ProtobufTreeModel)

- [x] 4.1 Modificar `ProtobufTreeModel` para assinar o `sinal_campo_alterado`. Se o campo alterado for usado como *label* do nó na árvore, emitir o sinal nativo `dataChanged` para atualizar só o texto.
- [x] 4.2 Conectar o `ProtobufTreeModel` aos sinais `sinal_item_adicionado` e `sinal_item_removido`.
- [x] 4.3 Implementar a inserção e remoção suave de nós na árvore utilizando as APIs nativas do Qt: `beginInsertRows()`/`endInsertRows()` e `beginRemoveRows()`/`endRemoveRows()`, preservando estado de expansão.

## 5. Integração Final e Testes

- [x] 5.1 Remover a reconstrução destrutiva (`load_node` e rebuild total da tree) que antes ocorria no `QUndoStack.indexChanged` do `WidgetEditorDados`.
- [x] 5.2 Escrever/atualizar testes de integração do `widget_editor_dados_historico_test.py` para validar a manutenção de Foco dos inputs e a preservação do estado do QTreeView.
