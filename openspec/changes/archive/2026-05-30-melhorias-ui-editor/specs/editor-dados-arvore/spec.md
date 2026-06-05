## MODIFIED Requirements

### Requirement: Exibição da Árvore de Dados do Croqui
O sistema SHALL exibir uma visão em formato de árvore listando hierarquicamente apenas as sub-mensagens contidas no `croqui.proto` que forem anotadas com a message option `MensagemFormatoUi.SEPARADO` ou `MensagemFormatoUi.ONEOF`. Outros campos escalares ou mensagens que não correspondam a essas opções não devem aparecer na árvore.
Para campos repetidos (`repeated`) dessas mensagens, a árvore deve apresentar um nó agrupador ("expando"), que ao ser expandido exibe os elementos da lista sequencialmente.
O recuo horizontal (indentação) da árvore SHALL ser compacto (12px) para preservar espaço horizontal.
O final de cada lista repetida na árvore SHALL conter um nó virtual interativo rotulado como `+ Adicionar [Tipo de Item]`.

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
