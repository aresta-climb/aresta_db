## ADDED Requirements

### Requirement: Opções customizadas de campo para UI
O sistema SHALL disponibilizar options de campo (extensões do `FieldOptions`) para guiar a renderização do editor de dados. As opções a serem criadas são `conteudo` (string), `mensagem` (string) e `conteudo_markdown` (bool), em adição as já existentes.

#### Scenario: Definição de conteudo_markdown
- **WHEN** uma string possui `[(aresta.conteudo_markdown) = true]`
- **THEN** o editor entenderá que este campo deve abrigar o conteúdo textual (como do markdown yaml frontmatter).

### Requirement: Opções customizadas de mensagem para formato UI
O sistema SHALL disponibilizar option de mensagem (extensão de `MessageOptions`) para ditar como a árvore do editor apresentará a mensagem: `mensagem_formato_ui` (string).

#### Scenario: UI Separada
- **WHEN** uma mensagem tem a option `[(aresta.mensagem_formato_ui) = "separado"]`
- **THEN** a UI deve exibi-la como um item separado na árvore, ao invés de mostrá-la inline.

### Requirement: Aplicação do ui_label
O arquivo de definição SHALL aplicar `[(aresta.ui_label) = "Valor"]` em campos onde o nome gerado automaticamente a partir da propriedade não for claro o suficiente para o usuário.

#### Scenario: Label de chave pix
- **WHEN** o campo se chamar `chave_pix_manutencao`
- **THEN** deve estar anotado com `[(aresta.ui_label) = "Chave Pix para Manutenção"]` ou equivalente.
