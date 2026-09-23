## ADDED Requirements

### Requirement: Reordenação de Itens em Coleções Repetidas via Botões
O sistema SHALL disponibilizar controles de movimentação rápida "Subir" (▲) e "Descer" (▼) em cada item pertencente a uma coleção repetida no formulário (`ContainerRepeatedWidget`).
- O botão "Subir" SHALL ser desabilitado quando o item for o primeiro da coleção (índice 0).
- O botão "Descer" SHALL ser desabilitado quando o item for o último da coleção (índice `N - 1`).
- Para coleções de item único (tamanho 1), ambos os botões SHALL permanecer desabilitados.
- Ao clicar em "Subir" ou "Descer", o sistema SHALL consolidar edições pendentes e despachar o comando no histórico de Undo/Redo (`CmdMoverRepeated`), garantindo reversibilidade total.

#### Scenario: Mover item para cima na lista
- **WHEN** o usuário clica no botão "Subir" de um item no índice 1 ou superior
- **THEN** o sistema SHALL trocar de posição o item com seu antecessor imediato no Protobuf via histórico, reposicionar o widget na interface e atualizar os estados dos botões.

#### Scenario: Mover item para baixo na lista
- **WHEN** o usuário clica no botão "Descer" de um item que não seja o último
- **THEN** o sistema SHALL trocar de posição o item com seu sucessor imediato no Protobuf via histórico, reposicionar o widget na interface e atualizar os estados dos botões.

#### Scenario: Desfazer e refazer reordenação por botão
- **WHEN** o usuário reordena um item via botão e em seguida executa Desfazer (Undo)
- **THEN** o sistema SHALL restaurar a posição original do item na coleção do Protobuf e no formulário.

### Requirement: Reordenação de Itens em Coleções Repetidas via Arrastar e Soltar
O sistema SHALL disponibilizar uma alça visual de arraste (`⠿`) em cada item de coleção repetida permitindo a reordenação direta por arrastar e soltar (drag-and-drop) dentro do mesmo container.
- O arraste SHALL iniciar apenas a partir da interação com a alça de arraste ou cabeçalho do item com distância mínima de arraste (para não conflitar com cliques de seleção e foco).
- Durante o arraste, o container SHALL exibir um indicador visual de inserção (linha horizontal) demarcando a posição de soltura entre os itens adjacentes.
- A soltura SHALL aceitar apenas itens da mesma coleção repetida de origem, ignorando eventos externos ou de outros campos.
- Ao soltar o item, o sistema SHALL consolidar edições pendentes, calcular o novo índice de destino e despachar o comando no histórico (`CmdMoverRepeated`).

#### Scenario: Reordenar item por arrastar e soltar
- **WHEN** o usuário arrasta um item pela alça e o solta em uma nova posição entre dois itens da mesma lista
- **THEN** o sistema SHALL mover o item para a posição correspondente no Protobuf via comando de histórico e reorganizar os widgets no layout.

#### Scenario: Desfazer e refazer reordenação por arrastar e soltar
- **WHEN** o usuário conclui um drag-and-drop na lista e aciona Desfazer (Undo)
- **THEN** o sistema SHALL retornar o item ao seu índice anterior no Protobuf e na interface gráfica.

### Requirement: Sincronização e Atualização Visual da Lista ao Mover
O sistema SHALL responder ao sinal `repeated_movido` emitido pelo modelo para sincronizar os widgets e propriedades da coleção repetida.
- Os índices armazenados nos widgets (`repeated_index`) e nos caminhos de campos primitivos (`protobuf_field`) SHALL ser atualizados para refletir a nova ordem contígua `0, 1, ..., N - 1`.
- Para sub-mensagens encapsuladas em itens colapsáveis (`WidgetColapsavel`), o prefixo de título do cabeçalho SHALL ser recalculado com o novo índice (ex: `Escalada [0]` -> `Escalada [1]`), preservando o estado de expansão (se o item estava aberto ou fechado) e eventuais títulos heurísticos.
- Os estados de habilitação dos botões "Subir" e "Descer" de todos os itens da coleção SHALL ser recalculados e atualizados imediatamente.

#### Scenario: Atualização de títulos indexados após movimentação
- **WHEN** um item colapsável é movido do índice 0 para o índice 2
- **THEN** o sistema SHALL atualizar o cabeçalho do item para refletir o novo índice `[2]`, assim como atualizar os índices dos itens intermediários que mudaram de posição.

#### Scenario: Atualização dos botões nos extremos da lista
- **WHEN** o primeiro item é movido para outra posição
- **THEN** o novo primeiro item da lista SHALL ter seu botão "Subir" desabilitado, e o item movido SHALL ter seus botões ajustados conforme sua nova posição.
