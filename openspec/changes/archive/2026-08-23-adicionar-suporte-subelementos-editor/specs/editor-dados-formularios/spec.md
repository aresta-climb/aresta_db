## ADDED Requirements

### Requirement: Cartões de Ação para Sub-elementos no Rodapé do Formulário
O sistema SHALL renderizar seções/cartões contextuais no rodapé da visualização de formulário para mensagens que possuem coleções repetidas de sub-elementos exibidos na árvore (ex: `Croqui`, `Pico`, `Grupo`, `Setor`, `ViaMultiplasEnfiadas`).
- Cada cartão SHALL exibir o título da coleção, a contagem atual de itens cadastrados e um botão de ação rápida para adicionar um novo item.
- Ao clicar no botão de adição do cartão, o sistema SHALL acionar a criação do novo elemento na coleção da mensagem atual através do histórico de Undo/Redo (`QUndoCommand`), atualizar a árvore de dados e selecionar o novo elemento para edição.

#### Scenario: Visualização do Cartão de Sub-elementos
- **WHEN** o formulário de uma mensagem que contém coleções filhas na árvore (ex: `Pico`) é carregado
- **THEN** o sistema SHALL renderizar no rodapé do formulário um cartão para cada coleção (ex: "Setores e Grupos"), contendo a contagem de itens e o botão de adição correspondente.

#### Scenario: Adição Rápida de Sub-elemento via Cartão do Formulário
- **WHEN** o usuário clica no botão de adicionar em um cartão de sub-elementos no formulário
- **THEN** o sistema SHALL empilhar a adição no histórico de Undo/Redo, criar o novo item na coleção da mensagem pai, refletir a alteração na árvore e focar no formulário do novo item criado.
