## MODIFIED Requirements

### Requirement: Menu de Contexto - Remoção e Reordenação
O sistema SHALL exibir um menu de contexto funcional e persistente que sobrevive a flutuações e re-layouts do Qt.

#### Scenario: Remoção de item novo
- **WHEN** o usuário adiciona um novo item e depois clica em "Excluir item"
- **THEN** o sistema SHALL excluir o item corretamente, não importando eventuais re-layouts em plano de fundo.
