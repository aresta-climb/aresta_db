## ADDED Requirements

### Requirement: Arquivo Protobuf Dedicado de Betas
O sistema SHALL isolar as mensagens e enums relacionados a mídias e betas em um arquivo `beta.proto` separado em `aresta_api/proto/`.

#### Scenario: Definição das estruturas em beta.proto
- **WHEN** o arquivo `beta.proto` é compilado
- **THEN** ele MUST conter as mensagens `MidiaBeta` (com URL, título, fonte, thumbnail e flags de agregação) e `MetaBeta` (com resumo de movimento/crux, agarras, confiança e reasoning).
- **THEN** ele MUST conter uma mensagem raiz `BetasPendentes` para serializar o arquivo intermediário `betas_pendentes.binarypb` agrupado por escalada.
- **THEN** todos os enums introduzidos MUST estar encapsulados em mensagens próprias e iniciar com `INDEFINIDO = 0`.

### Requirement: Integração com croqui.proto
O sistema SHALL importar `beta.proto` em `croqui.proto` para vincular as mídias às vias no arquivo compilado final.

#### Scenario: Importação em croqui.proto
- **WHEN** `croqui.proto` é compilado
- **THEN** ele MUST importar `beta.proto`.
- **THEN** a mensagem `Escalada` MUST conter o campo `repeated MidiaBeta betas = X;`.
