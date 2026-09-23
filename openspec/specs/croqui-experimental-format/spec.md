# croqui-experimental-format Specification

## Purpose
Define a estrutura e o ciclo de vida dos croquis experimentais no storage local.
## Requirements
### Requirement: Local Storage Structure
The system MUST save experimental croquis in the `croquis_experimentais` directory within the application's local storage. Each croqui MUST be contained in a root folder named `<timestamp_segundos>_<pais>_<estado>_<cidade>_<nome_do_pico>/`.

#### Scenario: Creating a new experimental croqui
- **WHEN** the system creates a new experimental croqui
- **THEN** it generates the correct folder name using the current timestamp and croqui metadata
- **AND** it creates the folder inside `croquis_experimentais`

### Requirement: Croqui Experimental Metadata
The root folder MUST contain a `croqui_experimental.yaml` file that adheres to the `CroquiExperimental` message schema defined in `aresta_api/proto/croqui_experimental.proto`, which includes the `commit_base_sha` field recording the Git commit hash of the official repository from which the experimental croqui was originated.

#### Scenario: Validating metadata
- **WHEN** the system reads an experimental croqui
- **THEN** it MUST parse `croqui_experimental.yaml` to retrieve the experimental croqui metadata including `commit_base_sha`

### Requirement: Database Directory Structure
The experimental croqui MUST contain a `database/` subdirectory matching the structure of a decompiled croqui. This directory MUST contain a `croqui.yaml` file, imported Markdown (`*.md`) parts, and an `imagens/` directory. O arquivo `croqui.yaml` conterá também o campo `ultima_migracao` e a nova lista de `botoes`.

#### Scenario: Decompiled data representation
- **WHEN** the user edits the croqui
- **THEN** the system updates the `croqui.yaml` and corresponding `*.md` files within the `database/` subdirectory

### Requirement: compilado Directory Structure
The experimental croqui MUST contain a `compilado/` subdirectory matching the structure of a compiled croqui. This directory MUST contain `indice.binarypb`, `compilado.binarypb` (with relative image paths), and an `imagens_geradas/` directory.

#### Scenario: Compiled data representation
- **WHEN** the system compiles the experimental croqui
- **THEN** it writes the outputs to the `compilado/` subdirectory, using paths relative to the croqui's root folder for images

### Requirement: Version Control Integration
The root folder of the experimental croqui MUST be initialized as a local Git repository (`.git`).

#### Scenario: Initializing version control
- **WHEN** a new experimental croqui is created
- **THEN** the system initializes a Git repository in the root folder to track local changes

