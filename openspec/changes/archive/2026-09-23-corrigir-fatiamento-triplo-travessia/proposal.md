## Why

Ao desenhar uma nova rota em mapas que termina com duplo clique sobre um nó existente de outra via, múltiplos pontos com snap idêntico disparam erroneamente a lógica de travessia topológica (`fatiar_linha_triplo`) com índices iguais (`idx_in == idx_out`), resultando em exceção não tratada `ValueError: Índices de entrada e saída inválidos para fatiamento triplo` e travamento da operação no Sentry.

## What Changes

- **Validação estrita de nós intermediários em travessias**: No controlador de mapas (`mapas_controller.py`), exigir que uma travessia possua ao menos dois nós distintos (`idx_in < idx_out`) estritamente intermediários (`0 < idx_in` e `idx_out < len - 1`), além de respeitar a ordem temporal do traçado (`pos_in < pos_out`).
- **Fallback resiliente na adição de rota**: Proteger a análise topológica de fatiamento contra exceções geométricas imprevistas, permitindo que a adição de rota reverta graciosamente para o caso simples (sem fatiamento) em vez de lançar exceção não capturada.
- **Higienização de pontos duplicados consecutivos**: Na visualização do editor de mapas (`widget_editor_mapas.py`), sanitizar a lista de pontos ao finalizar o traçado para descartar pontos consecutivos duplicados gerados por duplo clique ou cliques sobrepostos.
- **Reforço de contrato em `fatiar_linha_triplo`**: Em `topologia_trajeto.py`, explicitar a exigência de índices estritamente intermediários e com nós suficientes para que todas as 3 sublinhas resultantes sejam válidas (mínimo de 2 nós cada).

## Capabilities

### Modified Capabilities
- `tracados-vetoriais-mapas`: Especifica requisitos de robustez topológica para detecção de travessias, higienização de nós coincidentes por duplo clique e resiliência com fallback para traçados de vias.

## Impact

- `editor/controllers/mapas_controller.py`: Ajuste da detecção topológica de travessia e proteção com fallback gracioso.
- `editor/core/topologia_trajeto.py`: Validação aprimorada de limites em `fatiar_linha_triplo`.
- `editor/views/widget_editor_mapas.py`: Sanitização de pontos ao concluir o modo de nova rota.
- Testes unitários em `editor/core/topologia_trajeto_test.py`, `editor/controllers/mapas_controller_test.py` e `editor/views/widget_editor_mapas_test.py`.
