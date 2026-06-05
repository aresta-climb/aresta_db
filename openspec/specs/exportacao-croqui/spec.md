# exportacao-croqui Specification

## Purpose
Define os requisitos técnicos e de interface para a exportação de croquis experimentais no formato proprietário .croqui (ZIP ofuscado).
## Requirements
### Requirement: Exporting to .croqui format
O sistema MUST permitir a exportação de um croqui experimental para um arquivo com extensão `.croqui`. Este arquivo MUST ser um arquivo ZIP contendo todo o conteúdo da pasta do croqui experimental, mas com o primeiro byte ofuscado usando uma operação XOR com `0xFF`.

#### Scenario: Exportando com sucesso
- **WHEN** o usuário seleciona a opção de exportar e indica um caminho de destino válido
- **THEN** o sistema cria um arquivo ZIP temporário com o conteúdo da pasta
- **AND** aplica a ofuscação de magic number no arquivo resultante
- **AND** salva o arquivo com a extensão `.croqui` no local indicado

### Requirement: Interface de Exportação
O botão de exportar MUST abrir um diálogo de seleção de arquivo padrão do sistema operacional, pré-preenchido com o nome do croqui e a extensão `.croqui`.

#### Scenario: Abrindo diálogo de salvamento
- **WHEN** o usuário clica no botão "Exportar .croqui"
- **THEN** o sistema exibe um diálogo de salvamento filtrando por arquivos `.croqui`
- **AND** sugere um nome de arquivo baseado no ID do croqui experimental

