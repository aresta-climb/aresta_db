## 1. Mapeamento e Refatoração Inicial

- [x] 1.1 Localizar a classe derivada de `QGraphicsView` no arquivo `widget_editor_mapas.py` (ex: `MapView` ou equivalente).
- [x] 1.2 Adicionar variáveis de estado na classe (ex: `_arrastando_mapa: bool`, `_posicao_inicial_mouse: QPoint`, `_posicao_inicial_scroll: QPoint`).

## 2. Implementação dos Eventos de Mouse

- [x] 2.1 Sobrescrever `mousePressEvent`: verificar `itemAt(event.pos())`. Se não for um item interativo (fundo), ativar flag de arrasto e salvar posição atual.
- [x] 2.2 Sobrescrever `mouseMoveEvent`: se a flag de arrasto estiver ativa, calcular o delta e aplicar no `horizontalScrollBar().setValue()` e `verticalScrollBar().setValue()`.
- [x] 2.3 Sobrescrever `mouseReleaseEvent`: desativar flag de arrasto.
- [x] 2.4 Garantir que os eventos sejam repassados (`super().mousePressEvent(event)`, etc) quando o clique for sobre um POI ou quando não for o botão esquerdo do mouse.

## 3. Feedback Visual (Cursor)

- [x] 3.1 Implementar alteração de cursor no `mouseMoveEvent` (ou `hoverMoveEvent` / `viewportEvent`): se não estiver sobre um POI, definir cursor para `Qt.OpenHandCursor`.
- [x] 3.2 Alterar cursor para `Qt.ClosedHandCursor` durante o arrasto.
- [x] 3.3 Restaurar o cursor padrão caso o mouse esteja sobre um POI ou saia da View.

## 4. Testes e Validação

- [x] 4.1 Adicionar testes no `widget_editor_mapas_test.py` para simular cliques no fundo da imagem verificando alteração do scroll.
- [x] 4.2 Adicionar testes garantindo que o clique em um POI não ativa o pan e move o POI corretamente.
- [x] 4.3 Testar visualmente a interface para garantir a fluidez do pan e que a mudança de cursores não apresente conflitos (flickering).
