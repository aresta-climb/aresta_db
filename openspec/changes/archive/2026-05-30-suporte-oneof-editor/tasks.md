## 1. Atualizar aresta_api e Modelos

- [x] 1.1 Atualizar `editor/core/protobuf_tree_model.py` substituindo as referências a `ONEOF_CONTEUDO` por `ONEOF`
- [x] 1.2 Implementar transparência recursiva dinâmica para qualquer mensagem anotada com `ONEOF` no método `_resolve_transparency` de `ProtobufNode`
- [x] 1.3 Adicionar suporte à opção `titulo_na_ui` em `ProtobufTreeModel.data` para usar o valor do campo marcado como o título do nó, e para `ArquivoMarkdown` tentar extrair primeiro o título H1 do conteúdo, caindo de volta para o nome do arquivo caso indisponível

## 2. Ajustar Componentes de UI e Formulários

- [x] 2.1 Atualizar `editor/views/widget_editor_dados.py` para usar `ONEOF` no lugar de `ONEOF_CONTEUDO` na detecção de campos invisíveis na renderização inline
- [x] 2.2 Atualizar o carregamento e renderização de campos que possuem `oneof` para respeitar a opção `oneof_default` na criação e inicialização de novos elementos
- [x] 2.3 Implementar a lógica de exibição e edição do campo "Nome do arquivo:" no topo de formulários de itens externos em `WidgetFormularioPadrao`
- [x] 2.4 Desenvolver o componente split-pane `WidgetEditorMarkdown` para campos de markdown, com suporte a preview rico e atualização em tempo real

## 3. Implementar Gerenciamento de Arquivos Externos e Dimensionamento de Imagens

- [x] 3.1 Implementar carregamento recursivo de arquivos `.md` e parsing do YAML frontmatter na inicialização de `JanelaPrincipal` em `editor/views/area_principal.py`
- [x] 3.2 Implementar salvamento atomizado de croqui via cópia profunda (deep copy) e escrita ordenada de arquivos `.md` (frontmatter + markdown body)
- [x] 3.3 Adicionar lógica de renomeação segura de arquivos e deleção de arquivos físicos antigos obsoletos no disco
- [x] 3.4 Implementar `AutoScalingTextBrowser` com cálculo de proporção e redimensionamento dinâmico de imagens baseado no viewport para evitar scrollbars horizontais

## 4. Atualizar e Corrigir Testes

- [x] 4.1 Corrigir os testes unitários e de integração existentes em `editor/core/protobuf_tree_model_test.py` que usavam a propriedade `titulo` de `ArquivoMarkdown`
- [x] 4.2 Corrigir os testes em `editor/views/widget_editor_dados_test.py` e `editor/views/area_principal_e2e_test.py` que falharam devido à remoção de `ONEOF_CONTEUDO` ou mudança estrutural de `ArquivoMarkdown`
- [x] 4.3 Escrever novos testes unitários validando a criação automática baseada em `oneof_default` e a exibição de títulos baseada em `titulo_na_ui`
- [x] 4.4 Adicionar testes e2e cobrindo o ciclo de vida completo de carregamento, renomeação, e salvamento de arquivos externos `.md`
- [x] 4.5 Adicionar testes cobrindo a renderização split-pane de markdown e o dimensionamento dinâmico de imagens (`test_markdown_editor_image_auto_scaling`)
