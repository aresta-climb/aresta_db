## Why

O editor de mapas atualmente não permite arrastar a visualização do mapa (panning) clicando e arrastando no próprio fundo da imagem. Para facilitar a navegação em mapas grandes e manter o foco nas áreas de interesse, adicionar a capacidade de arrastar o mapa ao clicar fora de qualquer Ponto de Interesse (POI) melhora significativamente a experiência do usuário, tornando a navegação mais fluida e intuitiva.

## What Changes

- Adição de suporte a "click and drag" (clicar e arrastar) na área do mapa para realizar panning (arrastar a visualização).
- O arrasto só será ativado quando o clique inicial for em uma área de fundo (onde não exista um Ponto de Interesse / POI).
- Se o clique for feito sobre um POI, a interação continuará funcionando para selecionar ou mover o próprio POI (comportamento existente).
- O cursor do mouse poderá mudar para indicar a possibilidade de arrasto (ex: `Qt::OpenHandCursor` no hover, `Qt::ClosedHandCursor` ao arrastar) quando posicionado no fundo.

## Capabilities

### New Capabilities

- `mapa-arrastar-visualizacao`: Capacidade de navegação pelo mapa arrastando a visualização clicando no fundo da imagem, sem interagir com pontos de interesse.

### Modified Capabilities

- `editor-mapas`: O requisito do editor de mapas será expandido para incluir suporte explícito ao evento de arrasto e pan na visualização principal da imagem.

## Impact

- Impacto direto nas classes de visualização gráfica do mapa, provavelmente subclasses de `QGraphicsView` ou `QGraphicsScene` responsáveis por renderizar a imagem do mapa.
- Precisará gerenciar eventos de `mousePressEvent`, `mouseMoveEvent` e `mouseReleaseEvent` na visualização.
- Não deve haver impacto no modelo de dados ou na persistência YAML, tratando-se estritamente de uma melhoria de UI/UX.
