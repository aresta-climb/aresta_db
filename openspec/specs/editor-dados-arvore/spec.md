# editor-dados-arvore Specification

## Purpose
TBD - created by archiving change editor-dados. Update Purpose after archive.
## Requirements
### Requirement: Exibição da Árvore de Dados do Croqui
O sistema SHALL exibir uma visão em formato de árvore listando hierarquicamente apenas as sub-mensagens contidas no `croqui.proto` que forem anotadas com a message option `MensagemFormatoUi.SEPARADO` ou `MensagemFormatoUi.ONEOF`. Outros campos escalares ou mensagens que não correspondam a essas opções não devem aparecer na árvore.
Para campos repetidos (`repeated`) dessas mensagens, a árvore deve apresentar um nó agrupador ("expando"), que ao ser expandido exibe os elementos da lista sequencialmente.
O recuo horizontal (indentação) da árvore SHALL ser compacto (12px) para preservar espaço horizontal.
O final de cada lista repetida na árvore SHALL conter um nó virtual interativo rotulado como `+ Adicionar [Tipo de Item]`.
O parser e o modelador da árvore SHALL ser compatível com runtimes modernos do Protobuf que depreciaram o campo `.label`.

#### Scenario: Carregamento Inicial da Árvore Compacta
- **WHEN** a página de Editor de Dados é aberta
- **THEN** o sistema SHALL renderizar a árvore de dados com uma indentação compacta de 12px.

#### Scenario: Visualização do Nó Virtual de Adição Rápida
- **WHEN** uma lista de campos repetidos de mensagens é expandida na árvore
- **THEN** o sistema SHALL incluir um nó virtual `+ Adicionar [Item]` abaixo do último item da coleção.

#### Scenario: Adição Rápida via Nó Virtual
- **WHEN** o usuário seleciona ou clica no nó virtual `+ Adicionar [Item]`
- **THEN** o sistema SHALL criar o novo item na lista da mensagem pai, reconstruir a árvore mantendo o estado de expansão, expandir até o novo item e selecioná-lo automaticamente na árvore.

#### Scenario: Menu de Contexto - Adição
- **WHEN** o usuário clica com o botão direito sobre um nó agrupador (expando) da árvore
- **THEN** o sistema SHALL exibir um menu de contexto com a opção "Adicionar [Item]".

#### Scenario: Menu de Contexto - Remoção e Reordenação
- **WHEN** o usuário clica com o botão direito sobre um item pertencente a um campo repetido na árvore
- **THEN** o sistema SHALL exibir um menu contendo as opções:
  * "Excluir Item" (para remover o elemento correspondente).
  * "Mover para Cima" (para reordená-lo decrementando seu índice).
  * "Mover para Baixo" (para reordená-lo incrementando seu índice).
- **AND** o menu de contexto SHALL ser funcional e persistente, sobrevivendo a flutuações e re-layouts da árvore no Qt.

#### Scenario: Remoção de item recém-adicionado
- **WHEN** o usuário adiciona um novo item na árvore e em seguida clica em "Excluir item"
- **THEN** o sistema SHALL excluir o item corretamente, não importando eventuais re-layouts em plano de fundo que ocorram antes ou durante a exibição do menu de contexto.

### Requirement: Transparência de Wrappers de Arquivo
O sistema SHALL esconder os wrappers e mensagens marcadas com `MensagemFormatoUi.ONEOF` do usuário, exibindo e editando a sub-mensagem ou campo ativo diretamente. Ao criar ou inicializar um novo elemento de uma mensagem que inclui um `oneof`, o sistema SHALL selecionar automaticamente o campo com `oneof_default` se presente, ou solicitar a escolha caso contrário.

#### Scenario: Visualização e Edição de um nó Arquivo ou ONEOF
- **WHEN** a árvore ou o formulário encontram uma mensagem anotada com `MensagemFormatoUi.ONEOF`
- **THEN** o sistema SHALL apresentar as propriedades da sub-mensagem ou campo ativo referenciado como se fossem filhos diretos, omitindo a escolha estrutural do `oneof` em si.

#### Scenario: Salvamento de um nó Arquivo
- **WHEN** os dados de um sub-proto dentro de um wrapper de arquivo são modificados
- **THEN** o sistema SHALL assegurar que a sub-mensagem resultante seja salva em seu próprio arquivo externo, e o campo no `croqui.proto` principal seja configurado com a string de `caminho`, deixando a opção `conteudo` vazia/não definida.

#### Scenario: Criação de Novo Elemento com oneof_default
- **WHEN** o usuário adiciona um novo elemento que contém um `oneof` e um dos campos deste `oneof` possui a anotação `[(aresta.oneof_default) = true]`
- **THEN** o sistema SHALL pré-selecionar e inicializar esse campo por padrão.

#### Scenario: Criação de Novo Elemento Sem oneof_default
- **WHEN** o usuário adiciona um novo elemento que contém um `oneof` sem nenhuma opção marcada com `[(aresta.oneof_default) = true]`
- **THEN** o sistema SHALL exibir um diálogo para que o usuário escolha qual das opções do `oneof` deseja criar.

