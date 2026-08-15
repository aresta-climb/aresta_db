# windows-long-path-support Specification

## Purpose
TBD - created by archiving change fix-max-path. Update Purpose after archive.
## Requirements
### Requirement: Habilitação de Caminhos Longos no Windows
A aplicação MUST declarar suporte a caminhos de arquivos maiores que 260 caracteres no sistema operacional Windows.

#### Scenario: Instalação via MSIX
- **WHEN** a aplicação for instalada e empacotada via MSIX
- **THEN** o manifesto do aplicativo DEVE conter a declaração `longPathAware` ativada, permitindo que a API do Windows ignore o limite MAX_PATH tradicional
