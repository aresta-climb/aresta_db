## 1. Testes de Integração e Unidade (TDD First)

- [x] 1.1 Adicionar em `widget_editor_dados_test.py` os testes garantindo que listas (`repeated`) criam instâncias de `WidgetColapsavel` em vez de sub-frames totalmente expandidos.
- [x] 1.2 Implementar teste provando o comportamento Lazy Load: garantir que widgets de campos internos **não existem** no layout pai até que o acordeão receba `setChecked(True)`.
- [x] 1.3 Adicionar teste garantindo que o título do botão acordeão obedece à heurística (procura em `id`, `nome` e `titulo` da mensagem protobuf subjacente).
- [x] 1.4 Adicionar teste para o fluxo de **Undo/Redo**: se uma ação de "Desfazer" modificar o campo `nome` de uma sub-mensagem, o título do acordeão DEVE ser atualizado para refletir o nome antigo, mesmo que o acordeão esteja fechado e os widgets internos não tenham sido instanciados.

## 2. Componente Acordeão (CollapsibleBox)

- [x] 2.1 Criar a classe `WidgetColapsavel` (CollapsibleBox) implementando a interface com um `QToolButton` de cabeçalho e um `QFrame` interno para o conteúdo.
- [x] 2.2 Adicionar callback de inicialização "Lazy" que é disparado de forma garantida apenas na primeira abertura.
- [x] 2.3 Expor mecanismo (`update_title` ou equivalente) para que componentes pais solicitem o recálculo do título em caso de atualização de dados (útil no Undo/Redo).

## 3. Lógica Heurística para Títulos

- [x] 3.1 Criar função que extrai dinamicamente campos como `nome`, `id` ou `titulo` de uma mensagem protobuf para uso em rótulos na UI.
- [x] 3.2 Ligar essa função na inicialização do `WidgetColapsavel` dentro da tela.

## 4. Integração no Formulário Dinâmico e Tratamento de Eventos

- [x] 4.1 Substituir em `_renderizar_item_no_indice` do `WidgetFormularioPadrao` a criação do `QFrame` pela instanciação do `WidgetColapsavel`.
- [x] 4.2 Passar o `_render_message_fields(item_msg, frame_layout)` como o callback lazy do acordeão.
- [x] 4.3 Ajustar o listener `_on_campo_alterado` para ser resiliente a widgets ausentes (submensagens não abertas).
- [x] 4.4 Injetar no `_on_campo_alterado` a checagem: caso o campo modificado seja usado como rótulo do acordeão parente, instruí-lo a atualizar seu título na UI.
