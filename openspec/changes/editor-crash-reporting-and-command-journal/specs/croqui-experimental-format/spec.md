## MODIFIED Requirements

### Requirement: Croqui Experimental Metadata
The root folder MUST contain a `croqui_experimental.yaml` file that adheres to the `CroquiExperimental` message schema defined in `aresta_api/proto/croqui_experimental.proto`, which includes the `commit_base_sha` field recording the Git commit hash of the official repository from which the experimental croqui was originated.

#### Scenario: Validating metadata
- **WHEN** the system reads an experimental croqui
- **THEN** it MUST parse `croqui_experimental.yaml` to retrieve the experimental croqui metadata including `commit_base_sha`
