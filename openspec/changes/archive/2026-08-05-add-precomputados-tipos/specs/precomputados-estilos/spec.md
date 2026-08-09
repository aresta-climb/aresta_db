## ADDED Requirements

### Requirement: Detalhamento de estilo em pré-computados
O sistema DEVE expor nas estruturas de Pré-computados (Setor, Grupo, Pico e ResumoCroqui) a contagem de cada tipo de escalada.

#### Scenario: Compilação de croqui com estilos mistos
- **WHEN** um setor possui uma via esportiva, um boulder e uma via de múltiplas enfiadas
- **THEN** o nó compilado do setor DEVE registrar os contadores `total_esportivas = 1`, `total_boulders = 1` e `total_multiplas_enfiadas = 1`
- **THEN** o índice final (ResumoCroqui) DEVE propagar essas somatórias corretamente

#### Scenario: Omissão de contadores zerados
- **WHEN** um pico não possui nenhum boulder catalogado
- **THEN** o campo `total_boulders` do pré-computado DEVE ser omitido no YAML/JSON devido à sua nulidade, economizando tamanho de payload.
