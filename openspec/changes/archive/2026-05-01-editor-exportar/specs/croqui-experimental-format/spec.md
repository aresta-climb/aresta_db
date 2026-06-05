## MODIFIED Requirements

### Requirement: Import and Export functionality
O sistema MUST suportar a exportação de um croqui experimental comprimindo sua pasta raiz em um arquivo ZIP renomeado com a extensão `.croqui`, aplicando uma ofuscação de magic number (XOR 0xFF no primeiro byte). Inversamente, MUST suportar a importação de um arquivo `.croqui` realizando a desofuscação e extraindo seu conteúdo para o diretório `croquis_experimentais`.

#### Scenario: Exporting a croqui
- **WHEN** o usuário solicita a exportação de um croqui experimental
- **THEN** o sistema gera um arquivo `.croqui` contendo o conteúdo comprimido e ofuscado da pasta do croqui

#### Scenario: Importing a croqui
- **WHEN** o usuário importa um arquivo `.croqui`
- **THEN** o sistema realiza a desofuscação do cabeçalho
- **AND** extrai seu conteúdo para uma estrutura de pasta válida dentro de `croquis_experimentais`
