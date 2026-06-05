# undo-redo-graficos Specification

## Purpose
TBD - created by archiving change add-undo-redo. Update Purpose after archive.
## Requirements
### Requirement: Desfazer em QGraphicsScene
As operações de manipulação espacial de Bounding Boxes, Polígonos e Vértices nos mapas DEVEM gerar comandos de movimentação atômicos.

#### Scenario: Arrasto de Polígono no Mapa
- **WHEN** o usuário clica num polígono, arrasta com o mouse por múltiplos pixels e solta
- **THEN** apenas um único comando `CmdMoverPonto/Objeto` é inserido na pilha global, contendo a posição de clique inicial e a posição final de soltura.

