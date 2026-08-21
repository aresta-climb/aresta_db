## MODIFIED Requirements

### Requirement: Exibição da Árvore de Dados do Croqui
O sistema SHALL exibir uma visão em formato de árvore listando hierarquicamente apenas as sub-mensagens contidas no `croqui.proto` que forem anotadas com a message option `MensagemFormatoUi.SEPARADO` ou `MensagemFormatoUi.ONEOF`. Outros campos escalares ou mensagens que não correspondam a essas opções não devem aparecer na árvore.
Para campos repetidos (`repeated`) dessas mensagens, a árvore deve apresentar um nó agrupador ("expando"), mesmo quando a coleção estiver vazia (com 0 elementos), que ao ser expandido exibe os elementos da lista sequencialmente.
O recuo horizontal (indentação) da árvore SHALL ser compacto (12px) para preservar espaço horizontal.
O final de cada lista repetida na árvore SHALL conter um nó virtual interativo rotulado como `+ Adicionar [Tipo de Item]`.
O parser e o modelador da árvore SHALL ser compatível com runtimes modernos do Protobuf que depreciaram o campo `.label`.
Toda adição ou remoção de elementos acionada na árvore SHALL ser realizada via comandos na pilha global de histórico (Undo/Redo), garantindo reversibilidade.

#### Scenario: Carregamento Inicial da Árvore Compacta
- **WHEN** a página de Editor de Dados é aberta
- **THEN** o sistema SHALL renderizar a árvore de dados com uma indentação compacta de 12px.

#### Scenario: Visualização de Expandos e Nós Virtuais em Coleções Vazias
- **WHEN** uma mensagem estrutural (ex: `Croqui`, `Pico`, `Grupo` ou `Setor`) possui uma coleção repetida elegível com 0 elementos
- **THEN** o sistema SHALL renderizar o nó agrupador (expando) correspondente na árvore contendo o nó virtual `+ Adicionar [Item]`.

#### Scenario: Visualização do Nó Virtual de Adição Rápida
- **WHEN** uma lista de campos repetidos de mensagens é expandida na árvore
- **THEN** o sistema SHALL incluir um nó virtual `+ Adicionar [Item]` abaixo do último item da coleção (ou como único filho se a lista estiver vazia).

#### Scenario: Adição Rápida via Nó Virtual com Histórico
- **WHEN** o usuário seleciona ou clica no nó virtual `+ Adicionar [Item]`
- **THEN** o sistema SHALL empilhar um comando de adição no histórico de Undo/Redo, criar o novo item na lista da mensagem pai, reconstruir a árvore mantendo o estado de expansão, expandir até o novo item e selecioná-lo automaticamente na árvore.

#### Scenario: Menu de Contexto - Adição em Nó Agrupador
- **WHEN** o usuário clica com o botão direito sobre um nó agrupador (expando) da árvore
- **THEN** o sistema SHALL exibir um menu de contexto com a opção "Adicionar [Item]".

#### Scenario: Menu de Contexto - Adição em Nó Estrutural Pai
- **WHEN** o usuário clica com o botão direito sobre um nó de mensagem estrutural pai (ex: `Pico`, `Grupo`, `Setor`, `Croqui`)
- **THEN** o sistema SHALL exibir opções de menu para adicionar diretamente cada um dos seus sub-elementos elegíveis (ex: "Adicionar Setor ou Grupo...", "Adicionar Escalada...").

#### Scenario: Menu de Contexto - Remoção e Reordenação
- **WHEN** o usuário clica com o botão direito sobre um item pertencente a um campo repetido na árvore
- **THEN** o sistema SHALL exibir um menu contendo as opções:
  * "Excluir Item" (para remover o elemento correspondente via comando de histórico).
  * "Mover para Cima" (para reordená-lo decrementando seu índice).
  * "Mover para Baixo" (para reordená-lo incrementando seu índice).
- **AND** o menu de contexto SHALL ser funcional e persistente, sobrevivendo a flutuações e re-layouts da árvore no Qt.

#### Scenario: Remoção de item recém-adicionado
- **WHEN** o usuário adiciona um novo item na árvore e em seguida clica em "Excluir item"
- **THEN** o sistema SHALL excluir o item corretamente, não importando eventuais re-layouts em plano de fundo que ocorram antes ou durante a exibição do menu de contexto.
