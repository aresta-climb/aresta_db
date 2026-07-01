## Context

Atualmente, o editor de mapas (visualizador de imagens) suporta clicar e arrastar em Pontos de Interesse (POIs) para movê-los. No entanto, quando o usuário clica em uma área de fundo da imagem (onde não há um POI) e arrasta o mouse, nenhuma ação de navegação (panning) ocorre. Isso dificulta a exploração de mapas grandes (ou com muito zoom), exigindo o uso exclusivo de barras de rolagem. A adição da funcionalidade de clicar e arrastar no fundo para movimentar a visualização é um padrão de usabilidade comum (ex: Google Maps, visualizadores de PDF, editores de imagem) que aumentará a eficiência do usuário.

## Goals / Non-Goals

**Goals:**
- Permitir que o usuário clique e segure o botão do mouse sobre qualquer área de fundo do mapa para arrastar (pan) a visualização na janela.
- Alterar o cursor do mouse dinamicamente: indicar "mão aberta" (OpenHandCursor) no fundo e "mão fechada" (ClosedHandCursor) ao arrastar, se possível sem conflitar com o cursor dos POIs.
- Garantir que a funcionalidade existente de mover POIs continue funcionando perfeitamente (o clique em um POI tem precedência sobre o clique no fundo).

**Non-Goals:**
- Não iremos alterar a lógica de zoom.
- Não iremos alterar a forma como os POIs são criados, selecionados ou arrastados.
- Não iremos implementar suporte a gestos complexos (ex: pinch-to-zoom em touchpads) neste escopo, apenas o clique-e-arraste básico com o mouse.

## Decisions

1. **Substituição de Comportamento do MouseEvent no QGraphicsView/QGraphicsScene**:
   - *Decisão*: A funcionalidade de arrasto (panning) será implementada interceptando os eventos de mouse (`mousePressEvent`, `mouseMoveEvent`, `mouseReleaseEvent`) na classe de visualização (possivelmente uma subclasse de `QGraphicsView` usada pelo editor de mapas).
   - *Alternativa*: Usar a propriedade nativa `QGraphicsView::setDragMode(QGraphicsView::ScrollHandDrag)`.
   - *Por que não a alternativa nativa?*: O modo `ScrollHandDrag` nativo do Qt pode interferir com a seleção e movimentação de itens (POIs). Quando `ScrollHandDrag` está ativo, ele captura o clique do mouse no QGraphicsView, e isso pode bloquear o envio do evento para os POIs.
   - *Decisão Final*: Implementar manualmente. Ao receber um `mousePressEvent`, verificaremos se o clique ocorreu sobre algum item (`scene()->itemAt(...)`). Se não houver item interativo sob o clique (ou seja, é o fundo da imagem), ativamos uma flag interna de "arrastando mapa" e gravamos a posição inicial do clique e a posição atual da `scrollBar()`. No `mouseMoveEvent`, se a flag estiver ativa, calculamos o delta e movemos as barras de rolagem correspondentes. No `mouseReleaseEvent`, desativamos a flag.

2. **Gerenciamento do Cursor**:
   - O cursor padrão do fundo será atualizado para refletir que a área pode ser arrastada (quando sobre a imagem, mas não sobre um POI). Isso exigirá tratamento do evento `mouseMoveEvent` (sem clique) ou `hoverMoveEvent` para detectar se o mouse está sobre a área livre e trocar o cursor.

## Risks / Trade-offs

- **[Risco] Interferência com eventos de itens (POIs)**: Se a implementação dos eventos de mouse na View não repassar o evento (`event->ignore()` ou chamando `QGraphicsView::mousePressEvent(event)` corretamente) quando houver um clique num POI, a movimentação de POIs pode ser quebrada.
  - *Mitigação*: Testar exaustivamente o arrasto do POI contra o arrasto do fundo do mapa. Garantir que, se `itemAt()` retornar um POI válido, o evento seja despachado para o comportamento padrão sem interferência.
- **[Trade-off] Esforço manual vs. Funcionalidade Nativa**: Implementar o drag na mão (manipulando scrollbars) requer mais código do que usar `setDragMode`, mas fornece o controle absoluto necessário para não quebrar a interação com os POIs.
