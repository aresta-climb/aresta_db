## MODIFIED Requirements

### Requirement: Exibição da Árvore de Dados do Croqui
O sistema SHALL exibir uma visão em formato de árvore listando hierarquicamente apenas as sub-mensagens contidas no `croqui.proto` que forem anotadas com a message option `MensagemFormatoUi.SEPARADO` ou `MensagemFormatoUi.ONEOF`. Outros campos escalares ou mensagens que não correspondam a essas opções não devem aparecer na árvore.
Para campos repetidos (`repeated`) dessas mensagens, a árvore deve apresentar um nó agrupador ("expando"), mesmo quando a coleção estiver vazia (com 0 elementos), que ao ser expandido exibe os elementos da lista sequencialmente.
O recuo horizontal (indentação) da árvore SHALL ser compacto (12px) para preservar espaço horizontal.
O final de cada lista repetida na árvore SHALL conter um nó virtual interativo rotulado como `+ Adicionar [Tipo de Item]`.
O parser e o modelador da árvore SHALL ser compatível com runtimes modernos do Protobuf que depreciaram o campo `.label`.
Toda adição ou remoção de elementos acionada na árvore SHALL ser realizada via comandos na pilha global de histórico (Undo/Redo), garantindo reversibilidade.
Ao reordenar itens de campos repetidos na árvore ("Mover para Cima" ou "Mover para Baixo"), o sistema SHALL sincronizar as referências de mensagens dos nós da árvore e de seus descendentes com as instâncias ativas no Protobuf, descarregando preventivamente edições pendentes para garantir que o item movido e suas sub-mensagens permaneçam editáveis sem geração de nós órfãos.

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

#### Scenario: Reordenação de Item Preserva Integridade e Capacidade de Edição
- **WHEN** o usuário aciona "Mover para Cima" ou "Mover para Baixo" em um item da árvore de dados
- **THEN** o sistema SHALL atualizar a posição do item na árvore via histórico de Undo/Redo
- **AND** atualizar as referências internas de mensagens do nó movido e de seus sub-nós (descendentes) para as novas instâncias ativas do Protobuf
- **AND** permitir que o item e suas sub-mensagens sejam editados sem lançar erros de mensagem órfã.

#### Scenario: Flush Preventivo de Edições Pendentes ao Reordenar
- **WHEN** o usuário aciona a reordenação de um item enquanto houver edições pendentes agendadas em temporizadores de coalescência
- **THEN** o sistema SHALL consolidar e descarregar imediatamente as edições pendentes antes de efetuar o movimento na coleção do Protobuf.
