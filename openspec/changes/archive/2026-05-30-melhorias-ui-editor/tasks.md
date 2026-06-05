## 1. Escrever Testes Automatizados (Fase Red)

### 1.1 Testes de Integração e Fronteiras (Princípio IV)
- [ ] 1.1.1 Escrever teste de integração em `editor/views/widget_editor_dados_test.py` simulando o clique com o botão direito na árvore (menu de contexto) e verificando a adição, remoção e reordenação (mover para cima/baixo) de itens repetidos no Protobuf.
- [ ] 1.1.2 Escrever teste de integração validando o comportamento de clique no nó virtual `+` na árvore, garantindo a criação do item no Protobuf e a seleção automática dele na UI.

### 1.2 Testes Unitários de Componente (Princípio III)
- [ ] 1.2.1 Adicionar teste unitário validando que a indentação da árvore está configurada como 12px.
- [ ] 1.2.2 Adicionar teste unitário em `editor/views/widget_editor_dados_test.py` para garantir que campos com `formato_na_ui = INVISIVEL` não sejam renderizados nos formulários.
- [ ] 1.2.3 Adicionar teste unitário validando a constrição de largura máxima (`max-width`) para controles primitivos específicos e a presença de `QFrame` como card no formulário.

## 2. Implementar a Lógica de Produção (Fase Green)

### 2.1 Ajustes de Árvore e ProtobufTreeModel
- [ ] 2.1.1 Configurar indentação de `12px` e aplicar estilos QSS em `WidgetEditorDados`
- [ ] 2.1.2 Estender `ProtobufNode` com o atributo `eh_no_adicao` (booleano) em português brasileiro
- [ ] 2.1.3 Injetar o nó virtual de adição rápida `+ Adicionar [Item]` (com `eh_no_adicao = True`) no final de coleções repetidas de mensagens em `ProtobufTreeModel._populate_children`
- [ ] 2.1.4 Tratar seleção do nó virtual `eh_no_adicao` em `WidgetEditorDados._on_tree_selection_changed` para disparar comando de adição no Protobuf, reconstruir a árvore e focar no novo item

### 2.2 Menu de Contexto na Árvore de Dados
- [ ] 2.2.1 Conectar o sinal de clique direito `customContextMenuRequested` no `QTreeView`
- [ ] 2.2.2 Implementar ações no menu de contexto baseadas no nó selecionado (Adicionar, Excluir, Mover para Cima/Baixo)
- [ ] 2.2.3 Desenvolver salvamento e restauração do estado de expansão da árvore ao reordenar, adicionar ou remover itens para evitar colapsos indesejados da árvore

### 2.3 Visibilidade de Campos e Layout de Formulário em Cards
- [ ] 2.3.1 Pular a renderização de campos que possuem `formato_na_ui = INVISIVEL` em `_render_message_fields` e `_render_oneof`
- [ ] 2.3.2 Envolver cada campo renderizado em um `QFrame` estilizado como card
- [ ] 2.3.3 Adicionar restrições de largura máxima para campos curtos (números, strings curtas, combos)
- [ ] 2.3.4 Posicionar botões de presença (Adicionar/Remover) no canto superior direito de cada card de campo

## 3. Refatorar e Polir (Fase Refactor)

- [ ] 3.1 Revisar códigos para garantir que todas as novas variáveis, comentários e funções estejam estritamente em português brasileiro (Princípio I)
- [ ] 3.2 Garantir simplicidade de código e evitar abstrações prematuras nos componentes customizados de UI
