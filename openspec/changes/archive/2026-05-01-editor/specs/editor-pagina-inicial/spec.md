## ADDED Requirements

### Requirement: Layout da Página Inicial
A Página Inicial DEVE ser a visualização padrão quando nenhum croqui experimental ou oficial for explicitamente selecionado. Ela DEVE estar dividida em uma área de ações principais e uma área de listagem de croquis experimentais locais.

#### Scenario: Abertura da Aplicação
- **WHEN** a aplicação for iniciada e a área principal carregada
- **THEN** a aplicação DEVE exibir a "Página Inicial" na área direita principal

### Requirement: Ações de Gerenciamento de Croquis
A aplicação DEVE apresentar três botões distintos para iniciar a edição de croquis: Novo Croqui, Importar Croqui Experimental, Editar Croqui Oficial.

#### Scenario: Exibição das Opções
- **WHEN** a Página Inicial for renderizada
- **THEN** a interface DEVE apresentar os três botões citados claramente visíveis para o usuário

#### Scenario: Clique em Novo Croqui
- **WHEN** o usuário clicar no botão "Novo croqui"
- **THEN** a aplicação DEVE iniciar o fluxo que solicita dados básicos (país, estado, cidade, nome) e criar a nova estrutura na pasta de croquis experimentais (mock/placeholder para esta fase).

#### Scenario: Clique em Editar Croqui Oficial
- **WHEN** o usuário clicar no botão "Editar croqui oficial"
- **THEN** a aplicação DEVE apresentar uma lista dos croquis disponíveis na pasta `base_repo` e permitir que o usuário selecione um para converter em experimental (mock/placeholder para esta fase).

### Requirement: Listagem de Croquis Experimentais
A aplicação DEVE escanear a pasta de croquis experimentais no disco local do usuário e exibi-los em uma lista na Página Inicial.

#### Scenario: Exibição de Croquis Experimentais
- **WHEN** a Página Inicial for renderizada e existirem pastas de croquis experimentais em `%appdata%/aresta_editor/croquis_experimentais`
- **THEN** a interface DEVE listar cada croqui encontrado mostrando seu timestamp ou nome legível e data de última modificação
- **THEN** ao clicar duas vezes (double-click) em um croqui da lista, a aplicação DEVE abrir o espaço do Editor para este croqui (mock/placeholder para esta fase).
