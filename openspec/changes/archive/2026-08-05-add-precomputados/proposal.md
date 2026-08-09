## Why

Para que clientes (como o aplicativo frontend) possam exibir informações rápidas sobre um croqui ou pico (ex: "50 vias", "3 setores") sem precisarem percorrer toda a hierarquia de mensagens protobuf ou baixar o croqui inteiro. Esses dados podem ser agregados em tempo de compilação.

## What Changes

- Adição de estruturas de dados precomputadas nas mensagens `Setor`, `Grupo` e `Pico` do `croqui.proto`.
- Inclusão dos campos de totais no `ResumoCroqui` do `indice.proto`.
- Implementação de um módulo em `preparar_submissao_lib.py` para calcular esses dados bottom-up (Setor -> Grupo -> Pico).
- Atualização do `deploy_generated.py` para popular o índice com as informações extraídas da compilação.

## Capabilities

### New Capabilities
- `croqui-precomputados`: Inclusão de estatísticas e totais agregados (escaladas, setores e grupos) para exibição rápida em listas e cabeçalhos.

### Modified Capabilities

## Impact

- `aresta_api/proto/croqui.proto`: novos sub-protos e campos (retrocompatíveis, mas invisíveis na UI).
- `aresta_api/proto/indice.proto`: novos campos no ResumoCroqui.
- `scripts/preparar_submissao_lib.py` e `scripts/deploy_generated.py`: lógicas de injeção dos precomputados durante a compilação.
