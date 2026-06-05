# selecao-croqui-oficial Specification

## Purpose
TBD - created by archiving change editor-tela-de-carregamento. Update Purpose after archive.
## Requirements
### Requirement: Diálogo de Busca de Croquis Oficiais
A aplicação MUST fornecer um diálogo para que o usuário possa buscar e selecionar um croqui oficial do repositório para edição.

#### Scenario: Interface de Busca
- **WHEN** o diálogo de busca for aberto
- **THEN** ele MUST apresentar um campo de texto para busca filtrável e uma lista com todos os IDs de croquis obtidos a partir do arquivo `appdata/aresta_db/generated/indice.binarypb` do repositório sincronizado

#### Scenario: Filtragem de Croquis
- **WHEN** o usuário digitar no campo de busca
- **THEN** a lista MUST ser atualizada em tempo real para exibir apenas os croquis cujos nomes ou IDs correspondam ao texto digitado

#### Scenario: Seleção e Criação de Experimental
- **WHEN** o usuário selecionar um croqui da lista e confirmar
- **THEN** a aplicação MUST exibir uma barra de progresso de cópia
- **THEN** a aplicação MUST criar um novo croqui experimental utilizando o ID do croqui oficial selecionado
- **THEN** a aplicação MUST copiar os arquivos base (croqui.yaml, markdown, imagens) do diretório oficial para o novo diretório experimental
- **THEN** a aplicação MUST realizar um commit inicial no repositório `.git` local com os arquivos importados
- **THEN** a aplicação MUST atualizar a lista de histórico na tela de carregamento e fechar o diálogo de busca

