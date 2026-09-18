## 1. Testes Automatizados em Primeiro Lugar (TDD / Red)

- [x] 1.1 Criar testes unitários em `editor/views/tree_view_adapter_test.py` que reproduzem a desatualização das referências `ProtobufNode.message` após mover itens repeated (cima e baixo) e validar falha inicial
- [x] 1.2 Criar testes de integração em `editor/views/widget_editor_dados_test.py` simulando o fluxo de mover um setor para cima/baixo e em seguida editar campos primitivos/markdown, validando falha inicial com mensagem órfã
- [x] 1.3 Criar testes em `editor/views/widget_editor_dados_test.py` verificando a integridade e capacidade de edição de nós filhos populados (ex: trilhas ou vias sob o setor movido)
- [x] 1.4 Criar testes em `editor/views/widget_editor_dados_test.py` verificando que edições pendentes no `TemporizadorCoalescencia` são descarregadas antes da execução do comando de mover
- [x] 1.5 Criar testes em `editor/views/widget_editor_dados_test.py` para desfazer e refazer (Undo/Redo) de `CmdMoverRepeated` garantindo que as instâncias continuam válidas e editáveis

## 2. Implementação da Sincronização na Árvore e Formulário (Green)

- [x] 2.1 Implementar a sincronização recursiva de mensagens em `ProtobufTreeViewAdapter._on_item_movido` para atualizar `node.message` e seus filhos populados com as novas instâncias do Protobuf
- [x] 2.2 Implementar o método `forcar_consolidacao_pendente` em `FormularioPadrao` e integrá-lo no início de `_executar_mover_para_cima` e `_executar_mover_para_baixo` em `WidgetEditorDados`
- [x] 2.3 Implementar a invalidação/limpeza do cache de formulários (`cached_forms`) em `FormularioPadrao` para instâncias antigas substituídas pelo Protobuf
- [x] 2.4 Integrar no slot `_on_repeated_movido` a recarga do nó ativo no formulário se o item exibido atualmente tiver sido afetado pelo movimento (garantindo suporte a Undo/Redo)

## 3. Verificação, Refatoração e Cobertura (Refactor)

- [x] 3.1 Executar a suíte de testes completa do editor (`pytest editor/views/tree_view_adapter_test.py editor/views/widget_editor_dados_test.py`) garantindo que todos os testes passem
- [x] 3.2 Remover trechos obsoletos em `widget_editor_dados.py` (como `_atualizar_mapeamentos_apos_troca`) mantendo código limpo e idiomático
- [x] 3.3 Verificar cobertura de testes unitários (100% de cobertura nos arquivos modificados) em conformidade com as regras do repositório
