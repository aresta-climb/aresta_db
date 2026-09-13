## Context

No editor de mapas (ditor/views/widget_editor_mapas.py), a classe ItemTrajetoLinha herda de QGraphicsPathItem e representa o traçado contínuo de uma via ou boulder através de curvas de Bézier cúbicas interpoladas via Centripetal Catmull-Rom.

Atualmente, ItemTrajetoLinha não sobrescreve shape(). A implementação nativa do Qt para QGraphicsPathItem::shape() inclui a área delimitada pelo fechamento implícito do path (p.addPath(path)), o que transforma curvas abertas com concavidade em polígonos maciços para hit-testing. Adicionalmente, quando o item é selecionado, o Qt invoca qt_graphicsItem_highlightSelected(), desenhando uma caixa pontilhada retangular ao redor de todo o oundingRect().

## Goals / Non-Goals

**Goals:**
- Implementar shape() estrito em ItemTrajetoLinha usando QPainterPathStroker sem inclusão do miolo do path, confinando o hit testing a um tubo ao redor da linha com tolerância ergonômica de clique (ex: max(14.0, espessura + 8.0)).
- Substituir o retângulo tracejado nativo de seleção do Qt por um halo ou contorno de alto contraste desenhado diretamente ao longo do spline em paint().
- Garantir que as alças de nós (AlcaNoTrajeto), que possuem zValue = 120 e raio mínimo, continuem sendo clicáveis e arrastáveis sem qualquer interferência.
- Assegurar 100% de cobertura de testes unitários para a nova geometria de colisão e para a renderização de seleção.

**Non-Goals:**
- Não alterar o hit testing de itens de área (ItemBoundingRetangulo, ItemBoundingQuadrado, ItemBoundingCirculo, ItemBoundingPoligono), cujo preenchimento interior é deliberado.
- Não alterar a estrutura de dados Protobuf, APIs ou arquivos de persistência de croqui.

## Decisions

### 1. Hit Testing Estrito com QPainterPathStroker
- **Decisão**: Em ItemTrajetoLinha.shape(), instanciar QPainterPathStroker, configurar largura com base na espessura atual mais margem de tolerância (ex: max(14.0, float(self.pen().widthF()) + 8.0)), aplicar RoundCap, RoundJoin, e retornar stroker.createStroke(self.path()).
- **Por que não cálculo analítico manual de distância no mousePressEvent?**: O pipeline gráfico do Qt (QGraphicsScene::itemAt / items) já utiliza shape() internamente para despacho de eventos de mouse, hover e seleção. Ajustar shape() resolve nativamente tanto o clique quanto hover e cursor sem bifurcar a lógica de eventos da cena.
- **Alternativas consideradas**: Usar QPainterPathStroker apenas com a espessura original da linha (3px). Rejeitado porque exigir precisão de 1.5px do ponteiro do mouse frustra a usabilidade em resoluções altas.

### 2. Supressão da Caixa Retangular Tracejada e Desenho de Halo de Seleção
- **Decisão**: No método paint() de ItemTrajetoLinha:
  1. Detectar se option.state & QStyle.StateFlag.State_Selected é verdadeiro.
  2. Criar uma cópia do option (opt = QStyleOptionGraphicsItem(option)) e limpar a flag State_Selected antes de chamar super().paint(painter, opt, widget). Isso impede o Qt de pintar o retângulo tracejado no oundingRect.
  3. Quando selecionado, antes ou após desenhar o traço da via, desenhar um halo semi-transparente de alto contraste (ex: pen com cor branca e alfa 180, largura spessura + 6px, RoundCap on both ends) ao longo do self.path().
- **Alternativas consideradas**: Manter a caixa retangular tracejada padrão do Qt. Rejeitado porque polui a visualização e reforça a ideia de colisão retangular.

### 3. Preservação de Z-Order e Interação de Nós
- **Decisão**: AlcaNoTrajeto permanece como item filho com zValue = 120. Como o stroke da linha de travessia não mais cobrirá o espaço interno, o clique no nó de qualquer linha vizinha chegará diretamente a ele sem ser mascarado pela linha de travessia.

## Risks / Trade-offs

- **[Risco]** Cliques muito próximos ao traço da via poderem ser difíceis de acertar se a tolerância for pequena demais.
  -> **Mitigação**: Tolerância mínima de 14px de largura total (7px de margem para cada lado), garantindo ergonomia em qualquer nível de zoom sem invadir rotas vizinhas comuns.
- **[Risco]** Overhead de CPU ao chamar shape() frequentemente durante movimentação do cursor.
  -> **Mitigação**: createStroke em curvas com dezenas de nós leva microssegundos no C++ do Qt, não havendo impacto perceptível em taxas de 60fps.
