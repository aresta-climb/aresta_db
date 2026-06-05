## RENAMED Requirements

- FROM: editor-pagina-inicial
- TO: editor-tela-de-carregamento

## MODIFIED Requirements

### Requirement: Layout da Página Inicial
A Tela de Carregamento MUST ser a visualização de entrada da aplicação. Ela MUST ser um `QDialog` flutuante e compacto, exibido de forma centralizada na tela do usuário, dividido em uma área de ações principais no topo e uma área de histórico de croquis experimentais na base.

#### Scenario: Abertura da Aplicação
- **WHEN** a aplicação for iniciada e a tarefa de inicialização concluída
- **THEN** a aplicação MUST exibir a "Tela de Carregamento" como um diálogo independente

### Requirement: Ações de Gerenciamento de Croquis
A aplicação MUST apresentar três botões distintos: "Novo croqui", "Importar croqui experimental" e "Editar croqui oficial".

#### Scenario: Exibição das Opções
- **WHEN** a Tela de Carregamento for renderizada
- **THEN** a interface MUST apresentar os três botões citados claramente visíveis para o usuário

### Requirement: Listagem de Croquis Experimentais
A aplicação MUST escanear a pasta de croquis experimentais no disco local do usuário e exibi-los em uma lista na Tela de Carregamento. Se a lista estiver vazia, a aplicação MUST exibir uma mensagem informativa.

#### Scenario: Exibição de Croquis Experimentais
- **WHEN** a Tela de Carregamento for renderizada e existirem pastas de croquis experimentais
- **THEN** a interface MUST listar cada croqui encontrado mostrando seu nome legível
- **THEN** ao clicar em um croqui da lista, a aplicação MUST permitir a continuação do trabalho

#### Scenario: Histórico Vazio
- **WHEN** a Tela de Carregamento for renderizada e NÃO existirem croquis experimentais
- **THEN** a interface MUST exibir o texto "Nenhum croqui no histórico" na área da lista
