## MODIFIED Requirements

### Requirement: Croqui Experimental Metadata
The root folder MUST contain a `croqui_experimental.yaml` file that adheres to the `CroquiExperimental` message schema defined in `aresta_api/proto/croqui_experimental.proto`, which includes the `commit_base_sha` field recording the Git commit hash of the official repository from which the experimental croqui was originated. O campo legado `resumo_edicao` (tag `4`) MUST ser removido do esquema Protobuf com `reserved 4;` ao final de `CroquiExperimental` e MUST NOT ser preenchido, exigido ou exibido na criação, importação (via UI ou MCP) ou listagem de histórico de croquis experimentais.

#### Scenario: Validating metadata
- **WHEN** the system creates, imports, or reads an experimental croqui
- **THEN** it MUST parse and persist `croqui_experimental.yaml` to retrieve the experimental croqui metadata including `autores`, timestamps, `id_original`, and `commit_base_sha` without writing or displaying `resumo_edicao`
- **AND** `CroquiExperimental` MUST reserve tag `4` (`reserved 4;`), keep `resumo_edicao` absent from its Protobuf descriptor, and audit against any usage in codebase AST checks
