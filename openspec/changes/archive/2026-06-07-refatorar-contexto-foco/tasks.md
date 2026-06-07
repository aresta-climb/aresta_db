## 1. Utilitário de Contexto (TDD)

- [x] 1.1 Criar o arquivo de testes `editor/core/contexto_test.py` definindo os cenários esperados de parsing (100% coverage desejado).
- [x] 1.2 Implementar a classe `ContextoUIPath` em `editor/core/contexto.py` fazendo os testes de 1.1 passarem (ciclo red-green-refactor).

## 2. Refatoração da Camada Base (Histórico)

- [x] 2.1 Adicionar sinal `sinal_foco_requisitado(str)` em `GerenciadorHistorico` e atualizar `historico_test.py` para garantir que o sinal seja testado e coberto.

## 3. Roteamento Central (JanelaPrincipal)

- [x] 3.1 Implementar método `_on_foco_requisitado(uri)` na `JanelaPrincipal` conectado aos sinais do `CroquiModel` e do `GerenciadorHistorico`.
- [x] 3.2 O método deve avaliar o URI usando `ContextoUIPath`, trocar o índice do `QStackedWidget` e instruir os editores. Adicionar testes simulando a chegada do sinal.

## 4. Atualização de Views e Comandos do Protobuf

- [x] 4.1 Modificar `WidgetEditorDados._on_foco_requisitado` para usar `ContextoUIPath`. Atualizar `widget_editor_dados_test.py` para cobrir o uso do path.
- [x] 4.2 Alterar a obtenção de contexto na árvore (ex: em `WidgetEditorDados._on_tree_selection_changed`) para anexar o prefixo `page:dados/`. Garantir que os testes de controller continuem passando (corrigindo mocks).

## 5. Atualização dos Comandos de Mapa

- [x] 5.1 Atualizar testes do mapa (`editor_mapas_test.py`) para verificar se os comandos nativos recebem a string de contexto.
- [x] 5.2 Modificar `CmdMoverPonto` e testar se `historico.sinal_foco_requisitado(self.contexto_ui)` é emitido no `undo()` e `redo()`.
