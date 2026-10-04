# Tasks

## 1. Renomeação para Português e Sincronização no Painel de Referências

- [ ] 1.1 [TDD Red] Criar testes unitários em `editor/views/widget_painel_referencias_test.py` validando os novos textos ("Vincular Elementos" / "Vinculando..."), tooltips em português e a seleção automática do card ao alternar o botão de vinculação.
- [ ] 1.2 [Green] Implementar em `editor/views/widget_painel_referencias.py` a renomeação dos botões e tooltips de `CardReferencia` e conectar o toggle do botão à seleção automática do card (`selecionar_referencia`), verificando a aprovação dos testes.

## 2. Eliminação de Referência Órfã e Feedback Visual Imediato no Editor de Mapas

- [ ] 2.1 [TDD Red] Criar testes unitários em `editor/views/widget_editor_mapas_test.py` reproduzindo a alternância de referências sem retenção de estado anterior no hover out, o texto da barra superior em português ("MODO VINCULAÇÃO") e o toggle instantâneo de POIs (adicionar/remover) com destaque ciano imediato.
- [ ] 2.2 [Green] Implementar em `editor/views/widget_editor_mapas.py` a barra superior em português, a limpeza atômica de `referencia_linkagem_ativa` e precedência limpa em `remover_destaque_pois`, além do feedback visual síncrono em `tratar_clique_poi_linkagem`, verificando a aprovação dos testes.

## 3. Verificação de Cobertura e Integração

- [ ] 3.1 Executar a suíte de testes unitários de mapas com verificação de cobertura via pytest (`pytest editor/views/widget_painel_referencias_test.py editor/views/widget_editor_mapas_test.py --cov`), garantindo 100% de cobertura e zero regressões.
