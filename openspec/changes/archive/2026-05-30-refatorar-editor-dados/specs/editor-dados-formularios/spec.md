## MODIFIED Requirements

### Requirement: Geração Dinâmica de Formulários
O sistema SHALL criar e exibir formulários na área de edição principal contendo TODOS os campos da mensagem selecionada atualmente na árvore. Cada campo no formulário deve conter seu rótulo amigável (priorizando `ui_label` ou gerando a partir do nome do campo), sua descrição (comentário no protobuf) e controles/botões para gerenciar a presença e valores do campo (adicionar se não houver, modificar valor já existente ou remover se já houver). Mensagens anotadas com `MensagemFormatoUi.INLINE` devem ser exibidas recursivamente inline no mesmo formulário, separadas/delimitadas por bordas, não margens.

#### Scenario: Visualização Completa da Mensagem
- **WHEN** uma mensagem é selecionada na árvore
- **THEN** o sistema SHALL exibir todos os seus campos escalares e sub-mensagens inline em um único formulário contínuo na área principal.

#### Scenario: Edição Inline de Sub-mensagens
- **WHEN** um campo do tipo mensagem está anotado com `MensagemFormatoUi.INLINE`
- **THEN** o sistema SHALL renderizar seus sub-campos diretamente dentro de uma seção delimitada por bordas (não margens) do formulário pai.

#### Scenario: Gerenciamento de Presença de Valores
- **WHEN** um campo opcional ou repetido é exibido no formulário
- **THEN** o sistema SHALL prover botões para adicionar o valor (se ausente), modificar o valor (se presente) ou remover o valor (se presente).
