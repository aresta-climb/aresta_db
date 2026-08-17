# beta-model Specification

## Purpose
TBD - created by archiving change coleta-de-betas. Update Purpose after archive.
## Requirements
### Requirement: Arquivo Protobuf Dedicado de Betas
O sistema SHALL isolar as mensagens e enums relacionados a mídias e betas em um arquivo `beta.proto` separado em `aresta_api/proto/`.

#### Scenario: Definição das estruturas em beta.proto
- **WHEN** o arquivo `beta.proto` é compilado
- **THEN** ele MUST conter as mensagens `MidiaBeta` (com URL, título, fonte, thumbnail, snippets e resultado_llm), `ResultadoLLMBeta`, `EscaladaAlvoBusca` e `ViasExtraidasCroqui`.
- **THEN** ele MUST conter a mensagem `CandidatosBetaPorEscalada` enriquecida com `grau`, `nome_setor`, `nome_grupo`, `nome_pico`, `cidade` e `estado`.
- **THEN** ele MUST conter a mensagem raiz `BetasPendentes` para serializar tanto o arquivo `candidatos_brutos.yaml` quanto `betas_pendentes.binarypb`.
- **THEN** todos os enums introduzidos MUST estar encapsulados em mensagens próprias e iniciar com `INDEFINIDO = 0`.

### Requirement: Integração com croqui.proto
O sistema SHALL importar `beta.proto` em `croqui.proto` para vincular as mídias às vias no arquivo compilado final.

#### Scenario: Importação em croqui.proto
- **WHEN** `croqui.proto` é compilado
- **THEN** ele MUST importar `beta.proto`.
- **THEN** a mensagem `Escalada` MUST conter o campo `repeated MidiaBeta betas = X;`.

