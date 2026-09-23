## MODIFIED Requirements

### Requirement: Seletor de Cores de Alto Contraste para Elementos do Mapa
O sistema SHALL fornecer um seletor visual de cores no diálogo de edição e no menu de contexto dos elementos do mapa (linhas, círculos, retângulos, quadrados e polígonos), disponibilizando a paleta recomendada de alto contraste para rocha (Vermelho, Laranja, Amarelo, Verde Lima, Ciano, Roxo, Branco, Cinza), opção de cor personalizada e opção de restauração para a cor padrão do sistema, com suporte a `QUndoCommand`.

#### Scenario: Alteração de Cor de Traçado
- **WHEN** o usuário seleciona uma nova cor na paleta para uma linha existente
- **THEN** o sistema SHALL atualizar a cor da linha e de seus marcadores na cena imediatamente e registrar o comando de alteração de cor na pilha de histórico.

#### Scenario: Alteração de Cor de Formas Geométricas via Menu de Contexto
- **WHEN** o usuário clica com botão direito sobre um círculo, retângulo, quadrado ou polígono e seleciona uma cor da paleta ou uma cor personalizada
- **THEN** o sistema SHALL atualizar visualmente a borda e o preenchimento translúcido da forma geométrica na cena imediatamente, além das alças de vértices no caso de polígonos, e registrar a alteração no histórico de comandos (`QUndoStack`).

#### Scenario: Restauração da Cor Padrão do Sistema
- **WHEN** o usuário seleciona a opção "Padrão do Sistema" no submenu de cores de uma forma geométrica
- **THEN** o sistema SHALL remover a cor customizada do elemento, restaurar as cores originais da geometria (verde translúcido para círculos/retângulos e azul translúcido para polígonos) e registrar a alteração no histórico de comandos.

#### Scenario: Desfazer e Refazer Alteração de Cor
- **WHEN** o usuário executa desfazer (Undo) ou refazer (Redo) após alterar a cor de uma forma geométrica
- **THEN** o sistema SHALL atualizar a renderização do elemento na cena imediatamente para refletir a cor correspondente ao estado restaurado.
