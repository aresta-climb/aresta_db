# merge-dados-lapinha Specification

## Purpose
Define os requisitos para a mesclagem de dados (CSV) do croqui da Lapinha para o formato YAML correspondente, mapeando os dados através de identificadores únicos.

## Requirements

### Requirement: Atualização do ano por ID numérico
O sistema DEVE processar o arquivo CSV e mapear as vias com os arquivos Markdown utilizando a coluna `N°` do CSV para bater com a propriedade `ids` no YAML correspondente.

#### Scenario: Sucesso na associação
- **WHEN** o ID (ex: 20) for encontrado tanto no CSV quanto na lista de `referencias` do YAML
- **THEN** o script prossegue para injetar a informação de `Ano` na respectiva `via` do YAML.

### Requirement: Preservação de Nomenclatura YAML
O sistema DEVE manter o nome original da via presente no YAML do croqui (ex: "Ben moon") nos casos onde exista divergência textual com a coluna `Nome da Via` do CSV.

#### Scenario: Divergência de Nomes
- **WHEN** uma divergência for identificada (ex: CSV='Bem moon', YAML='Ben moon')
- **THEN** o nome do YAML é preservado intacto.
