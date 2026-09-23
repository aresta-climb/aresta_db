## 1. Core de Topologia e Validação de Limites

- [x] 1.1 Adicionar testes unitários em `editor/core/topologia_trajeto_test.py` cobrindo índices de entrada/saída não estritamente intermediários e nós insuficientes para `fatiar_linha_triplo`, verificando a falha esperada (TDD Red)
- [x] 1.2 Ajustar validação de limites em `fatiar_linha_triplo` em `editor/core/topologia_trajeto.py` para exigir `0 < indice_entrada < indice_saida < total_nos - 1` e verificar aprovação dos testes (TDD Green)

## 2. Detecção Robusta de Travessia e Fallback no Controller

- [x] 2.1 Adicionar testes em `editor/controllers/mapas_controller_test.py` simulando novo traçado com nós repetidos (duplo clique), nós idênticos (`idx_in == idx_out`), sentido temporal invertido e verificação de fallback gracioso (TDD Red)
- [x] 2.2 Refatorar a identificação de travessia em `editor/controllers/mapas_controller.py` para exigir nós únicos distintos ordenados (`pos_in < pos_out`), envolvendo o bloco em fallback defensivo com log de aviso (TDD Green)

## 3. Higienização de Pontos Consecutivos na View

- [x] 3.1 Adicionar testes em `editor/views/widget_editor_mapas_test.py` verificando a remoção de pontos consecutivos coincidentes ou com distância menor que 1px em `finalizar_modo_nova_rota` (TDD Red)
- [x] 3.2 Implementar a deduplicação de pontos consecutivos na finalização da rota em `editor/views/widget_editor_mapas.py` e verificar aprovação dos testes (TDD Green)

## 4. Verificação Geral e Cobertura

- [x] 4.1 Executar a suíte completa de testes do editor via `pytest editor/` e assegurar que todos os testes passam com 100% de cobertura e sem regressões
