## MODIFIED Requirements

### Requirement: Interações Ágeis no Editor Markdown e Registro no Histórico (Undo/Redo)
O editor Markdown (`WidgetEditorMarkdown`) SHALL oferecer múltiplos pontos de entrada para inserção rápida de imagens e registrar as modificações de texto na pilha de histórico (`QUndoStack`), garantindo digitação responsiva e sem congelamentos.
- **Botão na Interface**: O editor SHALL exibir um botão de ação "Inserir Imagem" no cabeçalho do painel de edição.
- **Arrastar e Soltar (Drag & Drop)**: Ao arrastar uma imagem externa para o editor, o sistema SHALL abrir o diálogo de importação com a imagem pré-carregada; ao arrastar uma imagem já existente da pasta `imagens/`, o sistema SHALL inserir diretamente a tag Markdown no ponto de soltura.
- **Colar da Área de Transferência (`Ctrl+V`)**: Ao acionar colar com uma imagem no clipboard, o sistema SHALL abrir o diálogo de importação rápida com a captura pré-carregada.
- **Autocompletar Inline**: Ao digitar `![` ou `(imagens/` no editor de texto, o sistema SHALL exibir uma lista suspensa com os nomes das imagens existentes na pasta `imagens/` para autocompletar.
- **Histórico Global**: A inserção da tag de imagem no texto SHALL disparar a alteração através do controlador do formulário (`controller.alterar_primitivo`), permitindo que a ação seja desfeita (`Ctrl+Z`) e refeita (`Ctrl+Y`) de forma sincronizada com o modelo.
- **Temporização de Coalescência na Digitação e Atualização**: O editor de texto Markdown SHALL aplicar uma biblioteca autossuficiente (`editor.core.temporizador_coalescencia.TemporizadorCoalescencia`) com atraso entre 200ms e 300ms na digitação, atualizando a pré-visualização renderizada e emitindo o comando para o modelo apenas quando o usuário pausar a digitação ou perder o foco do campo.
- **Prevenção de Duplo Render**: Ao receber notificação externa via `set_conteudo`, o editor SHALL comparar o conteúdo recebido com o texto atual e ignorar a re-renderização do preview e o re-escaneamento de imagens caso os textos sejam idênticos.

#### Scenario: Colar Imagem da Área de Transferência
- **WHEN** o usuário copia uma captura de tela para a área de transferência e pressiona Ctrl+V no editor Markdown
- **THEN** o sistema SHALL abrir o diálogo de importação com a captura de tela carregada e nome sugerido preenchido.

#### Scenario: Autocompletar Nome de Imagem Existente
- **WHEN** o usuário digita `(imagens/` no editor Markdown
- **THEN** o sistema SHALL exibir a lista de arquivos disponíveis na pasta `imagens/` para seleção rápida via teclado.

#### Scenario: Desfazer Inserção de Imagem
- **WHEN** o usuário insere uma imagem no Markdown e aciona a ação de Desfazer (Undo)
- **THEN** o sistema SHALL reverter o texto do editor para o estado anterior à inserção da imagem.

#### Scenario: Digitação Contínua com Coalescência no Preview e no Modelo
- **WHEN** o usuário digita múltiplos caracteres consecutivamente em intervalo menor que 200ms
- **THEN** o texto é exibido imediatamente no campo de edição e a atualização do preview e do modelo é postergada até que ocorra uma pausa de digitação.

#### Scenario: Prevenção de Duplo Render em Ciclo de Eco
- **WHEN** o editor Markdown recebe a confirmação de dado alterado via `set_conteudo` com o mesmo texto já digitado
- **THEN** o editor não deve invocar novamente a renderização Markdown nem o redimensionamento de imagens.
