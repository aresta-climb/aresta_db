## Why

Para apresentar informações mais detalhadas sobre os picos, grupos e o croqui como um todo na interface do usuário, precisamos expor os totais de cada estilo de escalada (ex: quantidade de vias esportivas, vias móveis, boulders, etc. existentes). Realizar esse cálculo em tempo de execução seria ineficiente; logo, a consolidação no deploy otimizará a performance e a usabilidade.

## What Changes

- Adição de novos contadores (`total_esportivas`, `total_moveis`, `total_boulders`, `total_multiplas_enfiadas`, `total_highlines`) nas mensagens de pré-computados (ResumoCroqui, Pico, Grupo, Setor).
- Os contadores são omitidos automaticamente da serialização YAML e Protobuf quando seus valores forem iguais a 0 (comportamento nativo do proto3).
- Expansão do algoritmo atual de agregação de `precomputados` para varrer os tipos de escalada dentro dos setores e repassar a somatória pelas hierarquias até o índice.

## Capabilities

### New Capabilities
- `precomputados-estilos`: Estatísticas por estilo de escalada injetadas nas estruturas do croqui e índice.

### Modified Capabilities
- Nenhuma.

## Impact

- `aresta_api`: Necessário alterar `croqui.proto` e `indice.proto` e regerar binários.
- `aresta_db`: Modificações pontuais em `preparar_submissao_lib.py` e `deploy_generated.py` para mapear os tipos (oneof).
- Necessidade de recompilar a pasta `generated/` refletindo os novos contadores onde o valor for > 0.
