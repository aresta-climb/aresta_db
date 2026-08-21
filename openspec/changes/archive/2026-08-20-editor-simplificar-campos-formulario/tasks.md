## 1. Schema Protobuf e Metadados (Princípio I)

- [x] 1.1 Adicionar opções de campo `booleano_texto_indefinido`, `booleano_texto_sim`, `booleano_texto_nao` no arquivo `aresta_api/proto/croqui.proto` e recompilar `croqui_pb2.py`.
- [x] 1.2 Atualizar campos booleanos existentes em `croqui.proto` com anotações semânticas customizadas em português.

## 2. Testes de Integração em Primeiro Lugar (Princípio V)

- [x] 2.1 Criar testes de integração em `editor/views/widget_editor_dados_historico_test.py` validando o ciclo completo: renderização sem botões `[Adicionar]`/`[Remover]`, edição direta de campos, esvaziamento de campo disparando remoção de presença, e verificação de reversibilidade completa via `QUndoStack` (Undo/Redo).
- [x] 2.2 Criar testes de integração em `editor/views/widget_editor_dados_test.py` validando o fluxo ponta a ponta de carregamento e salvamento YAML para campos de texto, booleanos tri-state, coordenadas e inteiros nullable.

## 3. Comandos de Histórico e Edição de Estado (Princípios II, IV, VII)

- [x] 3.1 Escrever testes unitários em `editor/commands/comandos_protobuf_test.py` que falhem inicialmente (Red) para o `ComandoAlterarPrimitivo` suportando `ClearField` quando o valor for `None` ou string vazia, e restaurando o estado anterior no `undo()`.
- [x] 3.2 Implementar as alterações em `ComandoAlterarPrimitivo` e `CroquiModel` para fazer os testes passarem (Green) e refatorar (Refactor).

## 4. Fábrica de Widgets e Controles Especializados (Princípios II, IV, VI)

- [x] 4.1 Escrever testes unitários em `editor/views/protobuf_widget_factory_test.py` que falhem inicialmente (Red) para a criação e configuração de `QComboBox` tri-state para booleanos, `QLineEdit` para floats/coordenadas e `QSpinBox` com valor nulo para inteiros.
- [x] 4.2 Implementar os métodos em `ProtobufWidgetFactory` para fazer os testes passarem (Green) e refatorar mantendo simplicidade (Refactor).

## 5. Renderizador de Formulários e Regra "Vazio = Ausente" (Princípios IV, VI, VII)

- [x] 5.1 Escrever testes unitários em `editor/views/widget_editor_dados_test.py` que falhem inicialmente (Red) verificando a remoção definitiva dos botões `[Adicionar]` e `[Remover]` no cabeçalho dos cards de campos.
- [x] 5.2 Modificar `_render_field_inner` em `editor/views/widget_editor_dados.py` para remover a renderização dos botões `[Adicionar]` e `[Remover]` e sempre renderizar o controle de edição apropriado.
- [x] 5.3 Implementar bindings de esvaziamento e presença em `_setup_primitive_widget` e no editor Markdown, despachando as alterações via `CroquiController` para a pilha de histórico `QUndoStack`.
- [x] 5.4 Implementar renderização direta e regra de presença para submensagens inline (`Coordenada`), limpando a submensagem caso todos os campos filhos fiquem vazios.

## 6. Verificação de Cobertura e Qualidade (Princípios I, III)

- [x] 6.1 Executar a suíte de testes completa do repositório garantindo 100% de sucesso.
- [x] 6.2 Verificar cobertura de testes dos módulos afetados (`editor/views/`, `editor/models/`, `editor/commands/`, `aresta_api/`) e garantir 100% de cobertura nos códigos novos/modificados, validando estritamente identificadores e comentários em português brasileiro (Princípio I).
