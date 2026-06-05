## 1. Protobuf e Compilação

- [x] 1.1 Adicionar a opção `option (aresta.mensagem_formato_ui) = SEPARADO;` às mensagens estruturais principais (`Pico`, `Grupo`, `Setor` e `Escalada`) em `aresta_api/proto/croqui.proto`
- [x] 1.2 Executar a compilação dos arquivos do Protobuf rodando `python build.py protos -f`

## 2. Reimplementação da Árvore de Mensagens

- [x] 2.1 Alterar `ProtobufNode` e `ProtobufTreeModel` em `editor/core/protobuf_tree_model.py` para atuar apenas no nível de abstração de mensagem, selecionando exclusivamente nós `SEPARADO` e `ONEOF_CONTEUDO`, agrupando coleções sob nós expandores/expando intermediários
- [x] 2.2 Atualizar a suíte de testes unitários da árvore em `editor/core/protobuf_tree_model_test.py` para cobrir o novo modelo baseado em mensagens `SEPARADO`/`ONEOF_CONTEUDO` e agrupamentos repetidos

## 3. Implementação do Formulário Dinâmico e Unificado

- [x] 3.1 Reimplementar o `WidgetFormularioPadrao` em `editor/views/widget_editor_dados.py` para exibir todos os campos da mensagem em um único formulário
- [x] 3.2 Adicionar botões para controle de presença do valor (adicionar, modificar e remover) para campos escalares, opcionais e repetidos
- [x] 3.3 Implementar a renderização recursiva e inline para sub-mensagens anotadas como `INLINE`, garantindo que apareçam delimitadas por bordas, não margens (ex: QFrame com borda) sob a mensagem pai no formulário
- [x] 3.4 Garantir a conectividade entre cliques em nós da árvore e o carregamento do formulário correspondente no `WidgetEditorDados`

## 4. Verificação de Testes e Correções

- [x] 4.1 Executar os testes em `pytest editor` e assegurar que todos passem sem falhas
- [x] 4.2 Realizar verificação final no editor executando a aplicação local
