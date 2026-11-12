## 1. Testes Automatizados (TDD - Red)

- [x] 1.1 Adicionar teste em `scripts/gerar_malha_estrada_lib_test.py` validando que um quadrante cortado pela fronteira de anel (`15 km`, `60 km`, `150 km`) ou pelo limite de `200 km` por estrada (possuindo ao menos um nó `<= 200 km` e um vencedor intrínseco ligeiramente `> 200 km`) elege o vencedor intrínseco oficial do quadrante inteiro, e que interseções com vias locais de menor hierarquia (`residential` em nó `tertiary`/`secondary`) não alteram o vencedor intrínseco entre picos.

## 2. Implementação (Green & Refactor)

- [x] 2.1 Atualizar a etapa 3 de `gerar_malha_estrada_pico` em `scripts/gerar_malha_estrada_lib.py` para calcular o grau de cruzamento estável por camada hierárquica (`rank <= 3`, `rank == 4`, `rank >= 5`), eleger o vencedor intrínseco de cada quadrante inteiro `(anel, ix, iy)` e ativar todos os quadrantes alcançados dentro de `200 km` por estrada em seus respectivos anéis.
- [x] 2.2 Executar `pytest` com 100% de cobertura em `scripts/gerar_malha_estrada_lib.py`, além de `ruff format`, `ruff check` e `mypy`.

## 3. Regeneração de Dados e Verificação de Colisão

- [x] 3.1 Regenerar `database/br_mg_lagoa_santa_gruta_da_lapinha/malha_estrada.yaml` e `database/br_mg_pedro_leopoldo_gruta_do_bau/malha_estrada.yaml`, compilar o catálogo com `scripts/deploy_generated.py` e medir o aumento percentual de colisão de pontos entre os dois picos.
