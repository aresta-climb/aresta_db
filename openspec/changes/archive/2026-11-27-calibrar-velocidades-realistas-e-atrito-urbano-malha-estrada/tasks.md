## 1. Testes Automatizados (TDD - Red)

- [x] 1.1 Atualizar e expandir os testes em `scripts/gerar_malha_estrada_lib_test.py` (e `editor/views/widget_mensagem_coordenada_test.py` se necessário) validando `VERSAO_ATUAL_MALHA_ESTRADA == 3`, a diferenciação entre rodovias pavimentadas, vias urbanas (`lit=yes` e `maxspeed <= 60`), rotatórias, vicinais `unclassified` sem pavimento explícito, estradas de terra (`surface`/`tracktype`/`track`) e a penalidade de atraso em cruzamentos (`grau >= 3`).

## 2. Implementação (Green & Refactor)

- [x] 2.1 Atualizar `VERSAO_ATUAL_MALHA_ESTRADA = 3`, `calcular_velocidade_sem_transito_kmh` e a penalidade de interseção em `_extrair_grafo_maior_componente` em `scripts/gerar_malha_estrada_lib.py`.
- [x] 2.2 Executar `pytest` garantindo 100% de cobertura comportamental nos arquivos alterados, além de `ruff format`, `ruff check` e `mypy`.

## 3. Regeneração das Malhas e Compilação do Catálogo

- [x] 3.1 Regenerar `database/br_mg_lagoa_santa_gruta_da_lapinha/malha_estrada.yaml` e `database/br_mg_pedro_leopoldo_gruta_do_bau/malha_estrada.yaml`, validar os novos tempos estimados a partir de Belo Horizonte (~1h00–1h05 para o Baú e ~1h05–1h10 para a Lapinha) e compilar `generated/` com `scripts/deploy_generated.py`.
