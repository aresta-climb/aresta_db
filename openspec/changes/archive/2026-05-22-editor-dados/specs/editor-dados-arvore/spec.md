## ADDED Requirements

### Requirement: Exibição da Árvore de Dados do Croqui
O sistema SHALL exibir uma visão em formato de árvore listando hierarquicamente todos os campos e sub-mensagens contidas no `croqui.proto`.

#### Scenario: Carregamento Inicial da Árvore
- **WHEN** a página de Editor de Dados é aberta
- **THEN** o sistema SHALL renderizar um `QTreeView` populado com a estrutura completa do croqui carregado na memória.

#### Scenario: Seleção de um Nó Comum
- **WHEN** o usuário seleciona um nó correspondente a um campo comum (string, int, repeated)
- **THEN** o sistema SHALL emitir um evento para que a área direita exiba o formulário de edição genérico apropriado.

### Requirement: Transparência de Wrappers de Arquivo
O sistema SHALL esconder os wrappers de arquivo (`ArquivoSetor`, `ArquivoGrupo`, `ArquivoMarkdown`, `ArquivoExterno`) do usuário, exibindo e editando o sub-proto diretamente. O salvamento SHALL ser forçado para utilizar sempre a opção `caminho` ao invés de `conteudo`.

#### Scenario: Visualização e Edição de um nó Arquivo
- **WHEN** a árvore ou o formulário encontram um campo que seja do tipo `ArquivoSetor`, `ArquivoGrupo`, `ArquivoMarkdown` ou `ArquivoExterno`
- **THEN** o sistema SHALL apresentar as propriedades do sub-proto referenciado como se fossem filhos diretos, omitindo a escolha estrutural do `oneof arquivo` (caminho/conteudo).

#### Scenario: Salvamento de um nó Arquivo
- **WHEN** os dados de um sub-proto dentro de um wrapper de arquivo são modificados
- **THEN** o sistema SHALL assegurar que a sub-mensagem resultante seja salva em seu próprio arquivo externo, e o campo no `croqui.proto` principal seja configurado com a string de `caminho`, deixando a opção `conteudo` vazia/não definida.
