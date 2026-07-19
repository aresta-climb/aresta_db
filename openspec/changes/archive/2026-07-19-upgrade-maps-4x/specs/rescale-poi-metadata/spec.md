## ADDED Requirements

### Requirement: Atualização Geométrica Proporcional de Pontos de Interesse
O sistema SHALL suportar a re-escala de todas as coordenadas geométricas (x, y, raio, largura, comprimento) de forma automática quando a imagem atrelada a esses pontos for substituída por uma imagem de diferentes dimensões (mas de mesma proporção ou canvas original).

#### Scenario: Redimensionamento de Imagem HD
- **WHEN** uma nova imagem HD (e.g. versão 4x) é adicionada substituindo a antiga
- **THEN** o sistema lê a escala calculando `fator = nova_dimensao / velha_dimensao` e multiplica todos os vértices/distâncias no metadata JSON e Markdown, persistindo a exata posição do POI.
