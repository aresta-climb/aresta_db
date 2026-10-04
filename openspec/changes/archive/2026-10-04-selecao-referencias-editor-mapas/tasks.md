# Tasks

## 1. Seleção no CardReferencia e Painel de Referências

- [x] 1.1 [TDD] Escrever testes unitários em `editor/views/widget_painel_referencias_test.py` cobrindo o clique em `CardReferencia`, o método `definir_selecionado`, a emissão dos sinais `referencia_selecionada` e `referencia_desmarcada`, e a alternância (toggle).
- [x] 1.2 Implementar `mousePressEvent`, método `definir_selecionado(selecionado: bool)` com estilização dinâmica e controle do card selecionado ativo em `CardReferencia` e `PainelReferencias`, verificando com `pytest editor/views/widget_painel_referencias_test.py`.
- [x] 1.3 [TDD] Escrever testes unitários em `editor/views/widget_painel_referencias_test.py` para o método público `selecionar_referencia(idx)` com rolagem automática (`ensureWidgetVisible`) e preservação do índice selecionado durante `atualizar_cards()`.
- [x] 1.4 Implementar a preservação da seleção ativa na reconstrução de cards em `atualizar_cards()` e a rolagem automática em `selecionar_referencia(idx)` no `PainelReferencias`.

## 2. Persistência de Destaque e Fallback no Editor de Mapas

- [x] 2.1 [TDD] Escrever testes unitários em `editor/views/widget_editor_mapas_test.py` garantindo que `remover_destaque_pois()` restaura o destaque em ciano de `self.referencia_selecionada` quando o cursor deixa o painel lateral (`hover_out`).
- [x] 2.2 Conectar os sinais de seleção do `PainelReferencias` em `WidgetEditorMapas`, armazenar `self.referencia_selecionada` e atualizar a cascata de fallback em `remover_destaque_pois()`.
- [x] 2.3 [TDD] Escrever testes unitários em `editor/views/widget_editor_mapas_test.py` cobrindo a pré-visualização temporária ao passar o cursor sobre outro card e a restauração do destaque da referência selecionada após a saída do hover.
- [x] 2.4 Implementar a desmarcação da referência ativa ao clicar em área neutra de fundo do mapa no `VisualizadorMapa`.

## 3. Seleção Bidirecional pelo Mapa e Validação Integrada

- [x] 3.1 [TDD] Escrever testes unitários em `editor/views/widget_editor_mapas_test.py` verificando que o clique com botão esquerdo sobre um POI em modo normal localiza a referência proprietária e aciona a seleção no `PainelReferencias`.
- [x] 3.2 Implementar a busca da referência proprietária e a seleção bidirecional ao clicar em POIs no mapa em `WidgetEditorMapas`.
- [x] 3.3 Executar a suíte de testes unitários (`pytest editor/views/widget_painel_referencias_test.py editor/views/widget_editor_mapas_test.py`) garantindo 100% de cobertura, sem regressões nos modos de linkagem e câmera.
