## ADDED Requirements

### Requirement: Local Storage Structure
The system MUST save experimental croquis in the `croquis_experimentais` directory within the application's local storage. Each croqui MUST be contained in a root folder named `<timestamp_segundos>_<pais>_<estado>_<cidade>_<nome_do_pico>/`.

#### Scenario: Creating a new experimental croqui
- **WHEN** the system creates a new experimental croqui
- **THEN** it generates the correct folder name using the current timestamp and croqui metadata
- **AND** it creates the folder inside `croquis_experimentais`

### Requirement: Croqui Experimental Metadata
The root folder MUST contain a `croqui_experimental.yaml` file that adheres to the `CroquiExperimental` message schema defined in `aresta_api/proto/croqui_experimental.proto`.

#### Scenario: Validating metadata
- **WHEN** the system reads an experimental croqui
- **THEN** it MUST parse `croqui_experimental.yaml` to retrieve the experimental croqui metadata

### Requirement: Database Directory Structure
The experimental croqui MUST contain a `database/` subdirectory matching the structure of a decompiled croqui. This directory MUST contain a `croqui.yaml` file, imported Markdown (`*.md`) parts, and an `imagens/` directory.

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

### Requirement: Import and Export functionality
The system MUST support exporting an experimental croqui by compressing its root folder into a ZIP archive renamed with the `.croqui` extension. Conversely, it MUST support importing a `.croqui` file by extracting it into the `croquis_experimentais` directory.

#### Scenario: Exporting a croqui
- **WHEN** the user requests to export an experimental croqui
- **THEN** the system generates a `.croqui` file containing the compressed contents of the croqui's folder

#### Scenario: Importing a croqui
- **WHEN** the user imports a `.croqui` file
- **THEN** the system extracts its contents into a valid folder structure within `croquis_experimentais`
