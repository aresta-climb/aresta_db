## 1. Testes e Infraestrutura (TDD)

- [x] 1.1 Criar testes em `area_principal_test.py` validando que a ação de salvar não trava o Event Loop (usando `qtbot.waitUntil`).
- [x] 1.2 Atualizar testes em `widget_editor_mapas_test.py` simulando o botão de câmera e exigindo `item_camera_overlay.isVisible() == True` e `scene() is not None`.
- [x] 1.3 Adicionar asserções nos testes da câmera para validar estritamente que a área de `item_camera_overlay.rect()` é maior que zero.
- [x] 1.4 Criar teste verificando se a flag `ItemIsMovable` dos POIs é desativada durante a iniciação do modo de linkagem e restaurada na parada.

## 2. Correção do Ajuste de Câmera

- [x] 2.1 Refatorar a criação do `ItemCameraOverlay` em `iniciar_modo_camera` para garantir que o item é adicionado corretamente à `visualizador.scene()`.
- [x] 2.2 Corrigir o fallback matemático das variáveis `w` e `h` para precaver contra instâncias de `scene_rect` vazio.
- [x] 2.3 Validar opacidade, Z-Value e rotinas do `paint()` de `ItemCameraOverlay` para certificar visibilidade acima do mapa.
- [x] 2.4 Rodar os testes recém-criados do mapa, resolver bugs remanescentes e confirmar 100% de coverage.

## 3. Refatoração do Salvamento (Thread de Background)

- [x] 3.1 Implementar mecanismo de snapshot na Main Thread: extrair cópia independente do modelo de dados antes de repassar à thread de background.
- [x] 3.2 Isolar a lógica atual de disco/banco de dados em uma classe assíncrona (`WorkerSalvar(QRunnable)`) que recebe o snapshot.
- [x] 3.3 Implementar indicação visual de progresso (label de "Salvando...") na UI no momento do clique, sem bloquear edições permitidas.
- [x] 3.4 Iniciar o worker via `QThreadPool`, marcando internamente o ponto da operação (estado do historico).
- [x] 3.5 No sinal `finalizado(bool)` na Main Thread, restaurar estado visual e usar o estado do historico registrado para avaliar se o `QUndoStack` continua limpo.
- [x] 3.6 Modificar `closeEvent` em `area_principal.py` para bloquear fechamento com um modal "Finalizando salvamento..." se um salvamento assíncrono estiver ocorrendo.
- [x] 3.7 Garantir no `JanelaPrincipal` que chamadas subsequentes ao botão de "Salvar" sejam ignoradas se `self._worker_salvar.isRunning()` for verdadeiro.
- [x] 3.8 Rodar testes gerais para assegurar estabilidade.m `area_principal_test.py` (conforme `PRINCIPIOS.md`), garantindo 100% de coverage para as lógicas síncronas e assíncronas, incluindo testes de modificação durante o save e comportamento de fechamento bloqueado.

## 4. Prevenção de Movimentação Acidental de POIs

- [x] 4.1 Em `widget_editor_mapas.py`, modificar `_aplicar_highlight_linkagem` ou criar lógica nas entradas e saídas do modo de linkagem.
- [x] 4.2 Iterar sobre os itens (`ItemInteresse`) presentes na `QGraphicsScene` e desabilitar a flag `QGraphicsItem.GraphicsItemFlag.ItemIsMovable` enquanto a linkagem ocorre.
- [x] 4.3 Garantir que a flag é restaurada ao sair do modo e rodar o conjunto de testes atualizado no passo 1.4 para validar.
