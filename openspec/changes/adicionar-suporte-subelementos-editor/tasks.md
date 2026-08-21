## 1. Testes de Integração em Primeiro Lugar (Princípio V)

- [ ] 1.1 Criar teste de integração de ponta a ponta (Red) em `editor/views/widget_editor_dados_test.py` simulando a abertura de um croqui recém-criado, verificando a presença de expandos vazios, adição de Setor/Grupo via árvore, menu de contexto e cartão de rodapé.
- [ ] 1.2 Criar teste de integração (Red) validando que as adições de sub-elementos realizadas via nó virtual, menu de contexto e cartões de rodapé podem ser desfeitas e refeitas via pilha de Undo/Redo (`controller.desfazer()` e `controller.refazer()`).

## 2. Adaptação da Árvore de Dados via TDD (Princípios I, IV e VII)

- [ ] 2.1 Criar testes unitários (Red) em `editor/views/tree_view_adapter_test.py` para verificar a criação de expandos e nós virtuais para coleções vazias (`picos`, `setores_ou_grupos`, `setores`, `escaladas`, `botoes`).
- [ ] 2.2 Implementar a lógica (Green) em `_collect_eligible_under_message` em `editor/views/tree_view_adapter.py` para inspecionar os descritores do Protobuf e incluir coleções repetidas elegíveis vazias.
- [ ] 2.3 Ajustar a rotina de rotulagem (Green) no nó virtual de adição para exibir o nome amigável correto para uniões (ONEOF) e tipos compostos em português.
- [ ] 2.4 Refatorar (Refactor) o código de `tree_view_adapter.py` garantindo simplicidade, sem duplicação e 100% em português brasileiro.
- [ ] 2.5 Executar e validar que todos os testes unitários de `tree_view_adapter_test.py` passam.

## 3. Menu de Contexto Estendido na Árvore via TDD (Princípios I, IV, VI e VII)

- [ ] 3.1 Criar testes unitários (Red) em `editor/views/widget_editor_dados_test.py` para verificar a presença e execução das opções de menu de contexto de clique com o botão direito nos nós pais (`Croqui`, `Pico`, `Grupo`, `Setor`).
- [ ] 3.2 Implementar as ações contextuais (Green) no método `_mostrar_menu_contexto_arvore` em `editor/views/widget_editor_dados.py`, despachando comandos através do `controller.adicionar_repeated()`.
- [ ] 3.3 Refatorar (Refactor) o menu de contexto mantendo código direto, declarativo e sem abstrações prematuras.
- [ ] 3.4 Executar e validar os testes do menu de contexto.

## 4. Cartões de Ação Rápida no Rodapé do Formulário via TDD (Princípios I, IV, VI e VII)

- [ ] 4.1 Criar testes unitários (Red) em `editor/views/widget_editor_dados_test.py` para verificar a renderização dos cartões de sub-elementos no rodapé e o clique no botão de adição.
- [ ] 4.2 Implementar a renderização declarativa dos cartões contextuais (Green) em `WidgetFormularioPadrao` em `editor/views/widget_editor_dados.py` para entidades estruturais com sub-elementos (`Croqui`, `Pico`, `Grupo`, `Setor`, `ViaMultiplasEnfiadas`).
- [ ] 4.3 Conectar a ação do botão do cartão (Green) ao método `controller.adicionar_repeated()` com diálogo para ONEOFs, garantindo sincronização com a árvore e histórico Undo/Redo.
- [ ] 4.4 Refatorar (Refactor) a estrutura dos cartões mantendo componentes nativos do Qt com visual limpo.
- [ ] 4.5 Executar e validar os testes unitários de formulário.

## 5. Validação de Cobertura e Conformidade Final (Princípios I, II, III, IV, V, VI e VII)

- [ ] 5.1 Executar a suíte de testes de integração e unitários completa (`pytest editor/`) e verificar 100% de aprovação.
- [ ] 5.2 Medir e validar 100% de cobertura de código nos módulos alterados (`pytest --cov=editor.views.tree_view_adapter --cov=editor.views.widget_editor_dados`).
- [ ] 5.3 Realizar auditoria de código para assegurar que 100% dos nomes de variáveis, funções, classes e comentários estejam em português brasileiro.
