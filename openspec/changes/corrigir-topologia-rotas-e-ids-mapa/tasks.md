## 1. Testes Unitários e de Integração (Fase Vermelha - TDD)

- [ ] 1.1 Escrever testes unitários em `editor/core/topologia_trajeto_test.py` para desambiguação sob demanda par a par, validando que:
  - Múltiplas rotas isoladas no mesmo mapa permanecem com nó final `PASSAGEM` e sem rótulo.
  - Convergências no mesmo topo recebem a mesma letra ('A') e tipo `FIM_TOP`.
  - Bifurcações de tronco/início compartilhado recebem letras sequenciais distintas ('A', 'B') e tipo `FIM_TOP`.
  - Rota isolada adicionada ao lado de uma bifurcação existente não ganha letra de topo.
- [ ] 1.2 Escrever testes unitários em `editor/core/topologia_trajeto_test.py` para `desembrulhar_setor`, `gerar_id_poi_disjunto_setor` e `calcular_proximo_numero_inicio_setor`:
  - Validar suporte a `Setor`, `ArquivoSetor` (com `conteudo.mapas`) e proxies `ReadOnlyProxy`.
  - Validar inspeção prioritária dos POIs do mapa ativo para geração de IDs disjuntos mesmo com setor nulo ou vazio.
- [ ] 1.3 Escrever teste em `editor/controllers/mapas_controller_test.py` para adição de rota em mapa com POIs não-linha pré-existentes (ex: círculos):
  - Validar que a busca pelo índice real de POI impede que círculos existentes sejam sobrescritos durante a desambiguação de topos.
  - Validar que novas rotas recebem IDs únicos (`linha_1`, `linha_2`...) e números de início sequenciais sem colisão.
- [ ] 1.4 Escrever teste de integração de Undo/Redo em `editor/controllers/mapas_controller_test.py`:
  - Validar que desfazer a adição de uma rota restaura o estado exato dos POIs existentes e remove completamente a nova rota da lista.
- [ ] 1.5 Escrever teste de integração de View em `editor/views/widget_editor_mapas_test.py`:
  - Validar que rotas criadas sucessivamente não compartilham seleção visual em ciano.
  - Validar que acionar Undo remove imediatamente os itens gráficos da nova linha da `QGraphicsScene` sem deixar elementos zumbis.

## 2. Implementação das Correções no Core e Controllers (Fase Verde - TDD)

- [ ] 2.1 Implementar `desembrulhar_setor` em `editor/core/topologia_trajeto.py` para extrair seguramente mapas e escaladas de qualquer envoltório (`Setor`, `ArquivoSetor` ou proxies).
- [ ] 2.2 Refatorar `desambiguar_topos` em `editor/core/topologia_trajeto.py` para comparar rotas par a par no grafo de traçados e atribuir `FIM_TOP` exclusivamente em casos reais de convergência ou bifurcação.
- [ ] 2.3 Atualizar `gerar_id_poi_disjunto_setor` e `calcular_proximo_numero_inicio_setor` em `editor/core/topologia_trajeto.py` para inspecionar prioritariamente o mapa ativo e o setor desembrulhado.
- [ ] 2.4 Corrigir o mapeamento de índice real em `adicionar_rota_com_tracado` de `editor/controllers/mapas_controller.py`:
  - Localizar `idx_real = list(msg_mapa_proxy.pontos_de_interesse).index(l_original)` antes de chamar `mover_poi`.
  - Passar os IDs do mapa ativo no conjunto de IDs reservados.
- [ ] 2.5 Ajustar `finalizar_modo_nova_rota` em `editor/views/widget_editor_mapas.py` para garantir que o setor passado ao controller seja sempre o setor do mapa ativo editado (`_obter_setor_atual()`).

## 3. Verificação, Cobertura e Refatoração (Fase Refactor)

- [ ] 3.1 Executar a suíte de testes com `pytest --cov` garantindo 100% de aprovação e 100% de cobertura nos arquivos modificados (`topologia_trajeto.py`, `mapas_controller.py`, `widget_editor_mapas.py`).
- [ ] 3.2 Validar que nenhuma regressão foi introduzida nos cenários existentes de fatiamento topológico, travessia tripla e substituição de imagens.
