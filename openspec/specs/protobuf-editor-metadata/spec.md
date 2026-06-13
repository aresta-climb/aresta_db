# protobuf-editor-metadata Specification

## Purpose
TBD - created by archiving change proto-metadata. Update Purpose after archive.
## Requirements
### Requirement: Opções customizadas de campo para UI
O sistema SHALL disponibilizar options de campo (extensões do `FieldOptions`) para guiar a renderização do editor de dados. As opções a serem criadas são `conteudo` (string), `mensagem` (string), `conteudo_markdown` (bool), `oneof_default` (bool) e `titulo_na_ui` (bool), em adição às já existentes.

#### Scenario: Definição de conteudo_markdown
- **WHEN** uma string possui `[(aresta.conteudo_markdown) = true]`
- **THEN** o editor entenderá que este campo deve abrigar o conteúdo textual (como do markdown yaml frontmatter).

#### Scenario: Definição de oneof_default
- **WHEN** um campo do oneof possui `[(aresta.oneof_default) = true]`
- **THEN** o editor identificará este campo como o padrão para criação automática.

#### Scenario: Definição de titulo_na_ui
- **WHEN** um campo possui `[(aresta.titulo_na_ui) = true]`
- **THEN** o editor usará o valor deste campo como título de exibição na árvore.

### Requirement: Opções customizadas de mensagem para formato UI
O sistema SHALL disponibilizar option de mensagem (extensão de `MessageOptions`) para ditar como a árvore do editor apresentará a mensagem: `mensagem_formato_na_ui` com valores do enum `MensagemFormatoUi.Enum`, incluindo agora o valor `MAPA`.

#### Scenario: UI Separada
- **WHEN** uma mensagem tem a option `[(aresta.mensagem_formato_na_ui) = SEPARADO]`
- **THEN** a UI deve exibi-la como um item separado na árvore, ao invés de mostrá-la inline.

#### Scenario: UI com Abstração Oneof
- **WHEN** uma mensagem tem a option `[(aresta.mensagem_formato_na_ui) = ONEOF]`
- **THEN** a UI deve ocultá-la na árvore e exibir diretamente seu campo ativo ou sub-mensagem.

#### Scenario: UI como Botão de Mapa
- **WHEN** uma mensagem tem a option `[(aresta.mensagem_formato_na_ui) = MAPA]`
- **THEN** a UI do formulário padrão deve ser suprimida, exibindo-se em vez disso um botão que direciona o usuário para a interface visual especializada (Editor de Mapas).

### Requirement: Aplicação do ui_label
O arquivo de definição SHALL aplicar `[(aresta.ui_label) = "Valor"]` em campos onde o nome gerado automaticamente a partir da propriedade não for claro o suficiente para o usuário.

#### Scenario: Label de chave pix
- **WHEN** o campo se chamar `chave_pix_manutencao`
- **THEN** deve estar anotado com `[(aresta.ui_label) = "Chave Pix para Manutenção"]` ou equivalente.

