## REMOVED Requirements

### Requirement: Reordenação de Itens em Coleções Repetidas via Botões
**Reason**: Os botões de texto soltos `▲` e `▼` na lateral direita causavam dispersão espacial, poluição visual e desalinhamento em janelas amplas. A reordenação por arrastar e soltar (drag-and-drop) via alça visual `⠿` provou-se mais intuitiva, direta e suficiente para a navegação.
**Migration**: Usuários utilizam a alça visual de arraste (`⠿`) em cada item da lista para reordenar livremente.

## MODIFIED Requirements

### Requirement: Cartões de Ação para Sub-elementos no Rodapé do Formulário
O sistema SHALL renderizar seções/cartões contextuais no rodapé da visualização de formulário para mensagens que possuem coleções repetidas de sub-elementos exibidos na árvore (ex: `Croqui`, `Pico`, `Grupo`, `Setor`, `ViaMultiplasEnfiadas`).
- Cada cartão SHALL exibir o título da coleção, a contagem atual de itens cadastrados e um botão de ação rápida posicionado na área inferior do cartão para adicionar um novo item.
- Ao clicar no botão de adição do cartão, o sistema SHALL acionar a criação do novo elemento na coleção da mensagem atual através do histórico de Undo/Redo (`QUndoCommand`), atualizar a árvore de dados e selecionar o novo elemento para edição.

#### Scenario: Visualização do Cartão de Sub-elementos
- **WHEN** o formulário de uma mensagem que contém coleções filhas na árvore (ex: `Pico`) é carregado
- **THEN** o sistema SHALL renderizar no rodapé do formulário um cartão para cada coleção (ex: "Setores e Grupos"), contendo a contagem de itens e o botão de adição posicionado no corpo inferior do cartão.

#### Scenario: Adição Rápida de Sub-elemento via Cartão do Formulário
- **WHEN** o usuário clica no botão de adicionar em um cartão de sub-elementos no formulário
- **THEN** o sistema SHALL empilhar a adição no histórico de Undo/Redo, criar o novo item na coleção da mensagem pai, refletir a alteração na árvore e focar no formulário do novo item criado.

### Requirement: Sincronização e Atualização Visual da Lista ao Mover
O sistema SHALL responder ao sinal `repeated_movido` emitido pelo modelo para sincronizar os widgets e propriedades da coleção repetida.
- Os índices armazenados nos widgets (`repeated_index`) e nos caminhos de campos primitivos (`protobuf_field`) SHALL ser atualizados para refletir a nova ordem contígua `0, 1, ..., N - 1`.
- Para sub-mensagens encapsuladas em itens colapsáveis (`WidgetColapsavel`), o prefixo de título do cabeçalho SHALL ser recalculado com o novo índice (ex: `Escalada [0]` -> `Escalada [1]`), preservando o estado de expansão (se o item estava aberto ou fechado) e eventuais títulos heurísticos.

#### Scenario: Atualização de títulos indexados após movimentação
- **WHEN** um item colapsável é movido do índice 0 para o índice 2
- **THEN** o sistema SHALL atualizar o cabeçalho do item para refletir o novo índice `[2]`, assim como atualizar os índices dos itens intermediários que mudaram de posição.

#### Scenario: Atualização dos botões nos extremos da lista
- **WHEN** o primeiro item é movido para outra posição
- **THEN** o sistema SHALL atualizar os índices e propriedades visuais de todos os itens reorganizados contiguamente.

### Requirement: Renderização Direta de Card Visual para Mapas em Coleções Repetidas
O sistema SHALL renderizar itens de coleções repetidas do tipo `Mapa` (ou com anotação `mensagem_formato_na_ui = MAPA`) diretamente como cartões visuais abertos, sem encapsulamento em accordion colapsável (`WidgetColapsavel`).
- **Barra de Controle Superior**: Cada cartão SHALL exibir no topo uma alça de arraste `⠿` na extremidade esquerda, o título composto pelo índice e nome do arquivo da foto (ex: `Mapa 0: Parede Principal`), e exclusivamente o botão de remoção discreto na extremidade direita.
- **Corpo Visual**: Cada cartão SHALL exibir uma miniatura com proporção preservada da imagem (`caminho_imagem_mapa`), as dimensões em pixels (`largura_mapa × altura_mapa`), o caminho relativo do arquivo e o botão de ação `Abrir no Editor de Mapas`.
- **Tratamento de Imagem Ausente**: Caso o arquivo da imagem não exista ou não possa ser lido, o cartão SHALL exibir um indicador visual de imagem ausente/placeholder sem interromper o fluxo da interface.

#### Scenario: Visualização de cartão de mapa no formulário
- **WHEN** o formulário de uma mensagem contendo mapas (ex: setor ou pico) é exibido
- **THEN** cada item da coleção de mapas SHALL ser renderizado como um cartão aberto com sua foto em miniatura, metadados de resolução e botão para o editor de mapas, exibindo na barra superior apenas a alça de arraste, o título e a ação de remoção à direita.

#### Scenario: Visualização de mapa sem arquivo de imagem
- **WHEN** um mapa cadastrado não possui arquivo de imagem disponível no disco ou na memória
- **THEN** o cartão correspondente SHALL exibir um marcador de "Sem Imagem" no espaço da miniatura e desabilitar ações que dependam da imagem física.

### Requirement: Atualização e Sincronização de Cards de Mapa na Reordenação
O sistema SHALL sincronizar os cartões visuais de mapas ao responder ao sinal de movimentação no modelo (`repeated_movido`).
- Os índices nos títulos dos cartões (`Mapa [i]`) SHALL ser atualizados para refletir a nova posição contígua.
- O reposicionamento do cartão no layout SHALL preservar a miniatura carregada e os metadados do mapa.
- A operação de movimentação SHALL ser despachada via comando no histórico (`CmdMoverRepeated`), garantindo reversibilidade com Desfazer (Undo) e Refazer (Redo).

#### Scenario: Reordenação de cards de mapa por botões ou arraste
- **WHEN** o usuário move um cartão de mapa para outra posição via alça `⠿`
- **THEN** o cartão do mapa com sua respectiva miniatura e dados SHALL se mover para a nova posição no layout
- **AND** os índices de todos os cartões da coleção SHALL ser atualizados contiguamente.

#### Scenario: Desfazer reordenação de card de mapa
- **WHEN** o usuário desfaz (Undo) uma movimentação de mapa
- **THEN** o cartão do mapa e sua miniatura SHALL retornar à posição anterior na listagem visual e no Protobuf.

## ADDED Requirements

### Requirement: Container Integrado e Ação de Adição no Rodapé para Coleções Repetidas
O sistema SHALL estruturar coleções repetidas (`ContainerRepeatedWidget`) com a ação de adição de novos itens posicionada obrigatoriamente no rodapé da lista/container, e nunca no cabeçalho superior direito.
- **Cabeçalho**: O cabeçalho da coleção SHALL conter apenas o título do campo e eventuais dicas/descrições contextuais.
- **Rodapé de Adição**: O rodapé da coleção SHALL conter o botão de adição de novo item (ex: `+ Adicionar Item`, `+ Adicionar Mapa`), alinhado de forma natural ao fluxo vertical de leitura após os itens existentes.
- **Container Integrado para Primitivos**: Para coleções de campos escalares (primitivos como strings e inteiros), os itens SHALL ser encapsulados em um container emoldurado (cartão integrado), com campos de entrada de texto com largura responsiva e separadores sutis entre as linhas.
- **Estado Vazio**: Quando a coleção repetida contiver 0 itens, o container SHALL exibir uma indicação textual suave de lista vazia (ex: "Nenhum item cadastrado.") acompanhada do botão de adição.

#### Scenario: Visualização de coleção repetida com itens
- **WHEN** o usuário visualiza um campo repeated (escalar, mapa ou colapsável) com itens existentes
- **THEN** o botão de adicionar novo item SHALL estar posicionado após o último item da lista no rodapé da coleção, e o cabeçalho superior SHALL não conter botões de ação à direita.

#### Scenario: Visualização de coleção repetida vazia
- **WHEN** o usuário visualiza um campo repeated sem nenhum item cadastrado
- **THEN** o container SHALL exibir uma mensagem de lista vazia e disponibilizar o botão de adição no rodapé.

### Requirement: Remoção Discreta de Itens em Coleções Repetidas
O sistema SHALL disponibilizar em cada linha ou cabeçalho de item de coleção repetida exclusivamente o controle de remoção posicionado na extrema direita.
- O botão de remoção SHALL utilizar ícone discreto (lixeira `fa5s.trash-alt`), sem texto redundante longo.
- O estilo visual do botão SHALL ser neutro (*ghost/flat*) em estado de repouso, destacando-se em tom de alerta suave apenas sob foco ou passagem do cursor do mouse (*hover*).
- Ao clicar no botão de remoção, o sistema SHALL consolidar edições pendentes e despachar o comando no histórico de Undo/Redo (`CmdRemoverRepeated`).

#### Scenario: Remoção de item através de ícone discreto
- **WHEN** o usuário clica no ícone de lixeira na extrema direita de um item de coleção repetida
- **THEN** o sistema SHALL remover o item via histórico de Undo/Redo, atualizar o container e permitir reversão total via Desfazer.

### Requirement: Adição Rápida via Tecla Enter em Campos Escalares Repetidos
O sistema SHALL permitir que o usuário adicione rapidamente novos itens em coleções de campos de texto escalares repetidos através da tecla `Enter`.
- Ao pressionar `Enter` em um campo de texto de item escalar que contenha texto preenchido, o sistema SHALL despachar a adição do novo item vazio no histórico (`CmdAdicionarRepeated`).
- O foco do teclado do sistema SHALL ser imediatamente transferido para o novo campo de texto criado.

#### Scenario: Pressionamento de Enter para adicionar próximo item
- **WHEN** o usuário está editando um campo de texto escalar repetido e pressiona `Enter`
- **THEN** um novo item é adicionado ao final da coleção via histórico e o cursor de foco é automaticamente posicionado no novo campo de entrada.
