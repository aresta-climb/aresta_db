## 1. Testes e Infraestrutura (TDD)

- [ ] 1.1 Criar testes em `area_principal_test.py` validando que a ação de salvar não trava o Event Loop (usando `qtbot.waitUntil`).
- [ ] 1.2 Atualizar testes em `widget_editor_mapas_test.py` simulando o botão de câmera e exigindo `item_camera_overlay.isVisible() == True` e `scene() is not None`.
- [ ] 1.3 Adicionar asserções nos testes da câmera para validar estritamente que a área de `item_camera_overlay.rect()` é maior que zero.
- [ ] 1.4 Criar teste verificando se a flag `ItemIsMovable` dos POIs é desativada durante a iniciação do modo de linkagem e restaurada na parada.

## 2. Correção do Ajuste de Câmera

- [ ] 2.1 Refatorar a criação do `ItemCameraOverlay` em `iniciar_modo_camera` para garantir que o item é adicionado corretamente à `visualizador.scene()`.
- [ ] 2.2 Corrigir o fallback matemático das variáveis `w` e `h` para precaver contra instâncias de `scene_rect` vazio.
- [ ] 2.3 Validar opacidade, Z-Value e rotinas do `paint()` de `ItemCameraOverlay` para certificar visibilidade acima do mapa.
- [ ] 2.4 Rodar os testes recém-criados do mapa, resolver bugs remanescentes e confirmar 100% de coverage.

## 3. Refatoração do Salvamento (Thread de Background)

- [ ] 3.1 Isolar a lógica atual de disco/banco de dados em uma classe assíncrona (como `WorkerSalvar(QRunnable)` ou classe customizada baseada no worker já existente em `core`).
- [ ] 3.2 Implementar bloqueio (desabilitar comandos chave da UI) e indicação visual de progresso (label ou barra de status de "Salvando...") no momento do clique.
- [ ] 3.3 Iniciar o worker usando um `QThreadPool` e conectar os sinais customizados `finalizado(bool)` e `erro(str)` na Main Thread.
- [ ] 3.4 Restaurar estado de bloqueio da UI e processar pop-ups de confirmação ou erro `QMessageBox` quando o slot de término for ativado.
- [ ] 3.5 Executar os testes de `area_principal_test.py` atualizados e certificar 100% de coverage para as lógicas síncronas e assíncronas do salvamento.

## 4. Prevenção de Movimentação Acidental de POIs

- [ ] 4.1 Em `widget_editor_mapas.py`, modificar `_aplicar_highlight_linkagem` ou criar lógica nas entradas e saídas do modo de linkagem.
- [ ] 4.2 Iterar sobre os itens (`ItemInteresse`) presentes na `QGraphicsScene` e desabilitar a flag `QGraphicsItem.GraphicsItemFlag.ItemIsMovable` enquanto a linkagem ocorre.
- [ ] 4.3 Garantir que a flag é restaurada ao sair do modo e rodar o conjunto de testes atualizado no passo 1.4 para validar.
