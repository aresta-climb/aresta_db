# renomeacao-croqui Specification

## Purpose
TBD - created by archiving change fix-croqui-duplication-on-rename. Update Purpose after archive.
## Requirements
### Requirement: Rastreador de ID Original
O sistema MUST salvar o `id_original` do croqui no seu arquivo local de metadados (`croqui_experimental.yaml`) sempre que o projeto for inicializado ou clonado da raiz oficial.

#### Scenario: Criação de novo croqui
- **WHEN** um usuário cria um novo croqui a partir da tela inicial
- **THEN** o sistema salva o ID solicitado dentro do campo `id_original` do arquivo `croqui_experimental.yaml`

### Requirement: Renomeação da Pasta Raiz
O sistema MUST renomear fisicamente a pasta raiz experimental do croqui sempre que identificar, durante o processo de salvamento, que o ID dos dados extraídos difere do ID gravado no nome do diretório físico.

#### Scenario: Edição e Salvamento de ID Alterado
- **WHEN** o usuário altera o ID do croqui na aba de dados e clica em Salvar
- **THEN** o sistema renomeia a pasta de trabalho (mantendo o timestamp original) e redireciona todas as instâncias ativas de salvamento contínuo para o novo caminho no disco

