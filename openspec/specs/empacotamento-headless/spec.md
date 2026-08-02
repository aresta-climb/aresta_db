## ADDED Requirements

### Requirement: Headless Croqui Packaging
O sistema MUST prover um utilitário de linha de comando (CLI) para criar e empacotar arquivos `.croqui` independentemente do Editor gráfico.

#### Scenario: Generating experimental croqui structure
- **WHEN** o CLI for invocado apontando para uma pasta em `database/<id>`
- **THEN** ele MUST instanciar uma pasta temporária seguindo o formato de croqui experimental (`<timestamp>_<id>`)
- **AND** inicializar o repositório `.git`, copiar a base de dados para `database/` e o compilado para `compilado/`

#### Scenario: Exporting the croqui file
- **WHEN** a estrutura temporária estiver montada
- **THEN** o CLI MUST empacotar (ZIP) a pasta raiz
- **AND** aplicar ofuscação no primeiro byte do arquivo via XOR 0xFF, salvando-o com a extensão `.croqui`
