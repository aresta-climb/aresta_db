## 1. Testes Base (Red)

- [x] 1.1 Em `widget_editor_dados_test.py`, adicionar um teste unitário confirmando que o lambda de remoção falha quando seu respectivo `QModelIndex` interno foi invalidado, exigindo explicitamente que as callbacks do menu de contexto referenciem a abstração segura `QPersistentModelIndex`.
- [x] 1.2 Em `widget_editor_dados_test.py`, adicionar um teste unitário simulando a adição de um sub-item em uma árvore com coleções irmãs repetidas (ex: 2 picos), de forma a evidenciar que a auto-seleção pelo método `_localizar_novo_idx` encontra um falso positivo no galho vizinho.

## 2. Refatoração e Solução (Green)

- [x] 2.1 Em `widget_editor_dados.py` -> `_exibir_menu_contexto`: Encapsular `index` e `index.parent()` em `QPersistentModelIndex` nas actions "Excluir item", "Mover para Cima", "Mover para Baixo" e "Adicionar Item".
- [x] 2.2 Em `widget_editor_dados.py` -> `_localizar_novo_idx`: Refatorar para que o `_localizar_no_por_indice` inicie sua busca não em `(0,0)`, mas com relação ao índice original do `expando_node` recém-inserido ou seu nó pai.
- [x] 2.3 Executar bateria inteira de testes em `widget_editor_dados_test.py` atestando que os dois novos cenários passam sem quebrar comportamentos base.
