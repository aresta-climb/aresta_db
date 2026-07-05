## ADDED Requirements

### Requirement: Suporte Visual para Formatos Quadrados
O sistema do editor SHALL renderizar os campos da mensagem `BoundingQuadrado` perfeitamente em modo inline, mantendo a responsividade e estilo da árvore de propriedades sem a necessidade de lógicas especiais para cada formato visual.

#### Scenario: Visualização do BoundingQuadrado
- **WHEN** um Ponto de Interesse contiver a marcação de `quadrado`
- **THEN** o editor exibirá as propriedades relativas (`x`, `y`, `lado`) de forma inline abaixo do nó expansível do ponto de interesse.
