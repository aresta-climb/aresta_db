## ADDED Requirements

### Requirement: Reordenação de Elementos por Arrastar e Soltar
O sistema SHALL permitir que itens pertencentes a campos repetidos elegíveis na árvore de dados (como setores ou grupos em um pico, e setores em um grupo) sejam reordenados através de interação de arrastar e soltar (drag-and-drop).
A interface da árvore SHALL exibir um indicador visual de inserção (linha horizontal entre os itens) durante o arraste e despachar o comando de histórico `CmdMoverRepeated` ao soltar o item na nova posição, garantindo total reversibilidade via Undo/Redo conforme o princípio de edições via histórico.

#### Scenario: Reordenação de setor dentro da mesma lista
- **WHEN** o usuário arrasta um setor e o solta em uma nova posição entre outros setores da mesma lista repetida
- **THEN** o sistema SHALL reordenar o setor na coleção, atualizar a exibição da árvore com a nova ordenação e empilhar o comando de reordenação no histórico.

#### Scenario: Desfazer e refazer reordenação via arrastar e soltar
- **WHEN** o usuário executa uma reordenação por arrastar e soltar e em seguida aciona a ação de Desfazer (Undo)
- **THEN** o sistema SHALL restaurar o item para sua posição e índice anteriores na árvore e no Protobuf.

### Requirement: Migração Hierárquica de Setores
O sistema SHALL permitir a migração hierárquica de setores entre diferentes elementos pais na árvore de dados através de interação de arrastar e soltar:
- De um `Pico` (`setores_ou_grupos`) para dentro de um `Grupo` (`setores`).
- De dentro de um `Grupo` (`setores`) para a raiz de um `Pico` (`setores_ou_grupos`).
- Entre dois `Grupos` distintos do mesmo pico ou croqui.

Toda migração hierárquica SHALL ser executada como um comando atômico no histórico de Undo/Redo (`CmdMigrarSetor`), transferindo os dados da mensagem `ArquivoSetor` entre os containers e atualizando os metadados de nome de arquivo (`caminho_novo`) de forma consistente.
Ao concluir a soltura, o grupo de destino SHALL ser expandido automaticamente e o setor migrado SHALL ser selecionado na árvore e exibido no painel de formulário.

#### Scenario: Mover setor da raiz do Pico para dentro de um Grupo
- **WHEN** o usuário arrasta um setor pertencente à raiz do Pico e o solta sobre um nó de Grupo (ou entre os setores desse grupo)
- **THEN** o sistema SHALL remover o `SetorOuGrupo` do Pico, inserir o `ArquivoSetor` na lista `setores` do Grupo de destino, atualizar a extensão de metadados `caminho_novo` adicionando o prefixo do grupo (`grupo_{slug_grupo}_{nome_arquivo}`), expandir o grupo e selecionar o setor.

#### Scenario: Mover setor de dentro de um Grupo para a raiz do Pico
- **WHEN** o usuário arrasta um setor pertencente a um Grupo e o solta na raiz do Pico (entre setores ou grupos do Pico)
- **THEN** o sistema SHALL remover o `ArquivoSetor` do Grupo, envelopá-lo em um `SetorOuGrupo`, inseri-lo na lista `setores_ou_grupos` do Pico, atualizar `caminho_novo` removendo o prefixo do grupo, e selecionar o setor na árvore.

#### Scenario: Mover setor entre dois Grupos distintos
- **WHEN** o usuário arrasta um setor de um Grupo de origem e o solta em um Grupo de destino diferente
- **THEN** o sistema SHALL transferir o `ArquivoSetor` para a lista `setores` do Grupo de destino e atualizar `caminho_novo` substituindo o prefixo do grupo anterior pelo prefixo do novo grupo.

#### Scenario: Desfazer e refazer migração de setor
- **WHEN** o usuário aciona Desfazer (Undo) após uma migração hierárquica de setor
- **THEN** o sistema SHALL retornar o setor à sua lista de origem e índice original, restaurar o valor anterior de `caminho_novo` e atualizar a árvore atomicamente.

### Requirement: Prevenção de Conflitos e Colisões de Arquivos na Migração
O sistema SHALL verificar previamente se o nome de arquivo calculado para o setor (`caminho_novo`) entra em colisão com qualquer arquivo já existente fisicamente no croqui ou agendado em memória por outro item.
Se houver colisão de nomes, o sistema SHALL abortar imediatamente o drop, cancelar a movimentação, manter o item na posição original sem poluir a pilha de Undo/Redo e exibir um diálogo de aviso ao usuário (`QMessageBox.warning`).

#### Scenario: Abortar soltura em caso de arquivo conflitante
- **WHEN** o usuário tenta soltar um setor cujo novo nome de arquivo resultante já existe no croqui
- **THEN** o sistema SHALL rejeitar o evento de soltura, manter o setor em sua posição original e exibir uma caixa de diálogo informando sobre a duplicidade de arquivo.

### Requirement: Validação Visual de Operações Inválidas de Soltura
O sistema SHALL validar as regras do schema Protobuf durante o arraste e exibir o cursor de ação proibida (`Qt.DropAction.IgnoreAction`) ao passar sobre alvos ilegais.
São estritamente proibidas as seguintes operações:
- Soltar um `Grupo` sobre outro `Grupo` ou sobre um `Setor`.
- Soltar um `Setor` sobre outro `Setor` (como filho).
- Arrastar ou soltar sobre nós virtuais de adição (`+ Adicionar ...`) ou nós agrupadores (expandos).

#### Scenario: Bloqueio visual ao arrastar Grupo sobre outro Grupo
- **WHEN** o usuário tenta arrastar um Grupo sobre outro nó de Grupo
- **THEN** o sistema SHALL indicar ação proibida e ignorar a soltura.
