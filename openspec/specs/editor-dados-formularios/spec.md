# editor-dados-formularios Specification

## Purpose
TBD - created by archiving change editor-dados. Update Purpose after archive.
## Requirements
### Requirement: Geração Dinâmica de Formulários
O sistema SHALL criar e exibir formulários na área de edição principal contendo TODOS os campos da mensagem selecionada atualmente na árvore (exceto os marcados como invisíveis), renderizando os controles de edição diretamente e sem a exibição de botões de Adicionar ou Remover no cabeçalho dos cards.
- **Cards de Campo**: Cada campo (primitivo ou sub-mensagem) SHALL ser renderizado dentro de um container do tipo Card (`QFrame` com borda fina e cantos arredondados) para demarcação visual clara.
- **Constrição de Largura**: Controles de edição primitivos curtos (números, strings curtas, combos, caixas de seleção) SHALL ter uma largura máxima configurada (ex: `150px` para números, `450px` para strings curtas) para evitar estiramento horizontal excessivo.
- **Ocultação de Campos Invisíveis**: Campos que possuam a opção de campo `formato_na_ui = INVISIVEL` no protobuf SHALL ser omitidos e não renderizados no formulário.
- **Regra Vazio = Ausente**: Campos de texto e markdown em branco SHALL ser automaticamente limpos no Protobuf (`ClearField`) e omitidos na serialização YAML; a inserção de dados SHALL restaurar sua presença.
- **Invalidação de Cache na Reordenação**: Ao reordenar itens, formulários em cache vinculados a instâncias anteriores desanexadas SHALL ser invalidados, assegurando que formulários reexibidos operem sobre a instância de mensagem ativa.

#### Scenario: Visualização de Campo Primitivo com Largura Constrita
- **WHEN** um campo primitivo (número ou string curta) é exibido no formulário
- **THEN** o controle de entrada correspondente SHALL respeitar o limite máximo de largura, não ocupando toda a extensão horizontal da tela.

#### Scenario: Ocultação de Campo com formato_na_ui Invisível
- **WHEN** o formulário é gerado para uma mensagem contendo campos anotados como `[(aresta.formato_na_ui) = INVISIVEL]`
- **THEN** o sistema SHALL pular a renderização desses campos, deixando-os ocultos ao usuário.

#### Scenario: Renderização Direta de Campos sem Botões de Presença
- **WHEN** o formulário é renderizado para uma mensagem do Protobuf
- **THEN** os controles de entrada de texto, números, booleanos e submensagens inline SHALL ser exibidos diretamente no card, sem exibir botões de "Adicionar" ou "Remover" no cabeçalho do campo.

#### Scenario: Esvaziamento de Campo de Texto
- **WHEN** o usuário apaga todo o texto de um campo de string ou markdown
- **THEN** o sistema SHALL remover o campo via `ClearField` no modelo do Protobuf e omiti-lo na serialização YAML.

#### Scenario: Atualização e Invalidação de Formulário após Reordenação
- **WHEN** um elemento de coleção repetida é reordenado na árvore de dados
- **THEN** o sistema SHALL invalidar o formulário em cache associado à instância anterior do elemento
- **AND** renderizar/carregar o formulário vinculado à nova instância ativa do elemento, conectando seus controles de edição à mensagem correta do croqui.

### Requirement: Documentação e Textos da Interface Guiados pelo Protobuf
O sistema SHALL extrair dinamicamente a documentação de cada campo (explicações e descrições exibidas na UI) dos comentários presentes nos arquivos `.proto`. Da mesma forma, os rótulos (labels) dos campos SHALL ser extraídos dos nomes dos campos no protobuf ou de field/message options explicitamente definidos, de forma a não haver strings de documentação "hardcoded" na aplicação do editor.

#### Scenario: Visualização da Documentação de um Campo
- **WHEN** o formulário de um campo é exibido
- **THEN** o sistema SHALL mostrar o comentário presente no arquivo `.proto` (referente àquele campo) como documentação associada a ele na tela.

#### Scenario: Uso de Opções para Nomenclatura
- **WHEN** um campo do protobuf contém uma opção customizada (ex: referente a UI label)
- **THEN** o sistema SHALL priorizar essa string para o título/label do campo em vez do próprio identificador base do campo.

### Requirement: Edição de Arquivos Externos e Nome de Arquivo na UI
O sistema SHALL exibir um campo editável "Nome do arquivo:" no topo do formulário para qualquer mensagem correspondente a um arquivo externo (ex: `Setor`, `Grupo` ou `ArquivoMarkdown`).
- **Comportamento**: A alteração desse campo SHALL atualizar o nome do arquivo mapeado em memória para o elemento. Para novos elementos inseridos na árvore, o sistema SHALL gerar automaticamente um nome de arquivo único e amigável com a extensão `.md` (ex: `setor_nome_do_setor.md`).

#### Scenario: Visualização do Campo Nome do Arquivo
- **WHEN** um formulário de um item salvo em arquivo externo é carregado
- **THEN** o sistema SHALL exibir o campo "Nome do arquivo:" no topo do formulário contendo o nome atual do arquivo.

#### Scenario: Inicialização de Nome para Novo Item
- **WHEN** um novo setor ou grupo externo é adicionado à árvore de dados
- **THEN** o sistema SHALL gerar automaticamente um nome de arquivo baseado no tipo e no nome do elemento com a extensão `.md`.

### Requirement: Editor de Markdown Rico (Split-Pane)
O sistema SHALL exibir um editor em painel dividido (split-pane) para campos do tipo string que possuam a opção `conteudo_markdown = true` no protobuf ou tipo mime `text/markdown`.
- **Lado Esquerdo**: Editor de texto puro (`QTextEdit`) com fonte monoespaçada para edição direta do código markdown.
- **Lado Direito**: Um visualizador rico (`QTextBrowser`) exibindo a pré-visualização formatada do markdown em tempo real.

#### Scenario: Visualização do Editor Dividido
- **WHEN** um campo configurado para markdown é exibido no formulário
- **THEN** o sistema SHALL renderizá-lo usando o componente de painel dividido side-by-side.

### Requirement: Pré-visualização com Resolução de Caminhos e Dimensionamento de Imagens
A pré-visualização do markdown SHALL formatar e exibir imagens dinamicamente.
- **Frontmatter**: O sistema SHALL ignorar o YAML frontmatter (linhas entre `---` e `---` no topo) ao renderizar o markdown no painel de pré-visualização.
- **Caminhos de Imagens**: O sistema SHALL obter o diretório raiz do croqui a partir do modelo de dados (`CroquiModel`) e configurar o `baseUrl` do documento para resolver caminhos de imagens locais (ex: `imagens/...`).
- **Dimensionamento Responsivo**: O sistema SHALL redimensionar dinamicamente as imagens exibidas para que caibam perfeitamente na largura do painel do visualizador (sem ultrapassar a largura disponível e sem criar barras de rolagem horizontais).

#### Scenario: Dimensionamento de Imagem no Visualizador
- **WHEN** o visualizador rico renderiza o markdown ou sofre um redimensionamento de janela
- **THEN** o sistema SHALL ajustar proporcionalmente as dimensões de cada imagem (`QTextImageFormat`) para caber na largura livre do viewport.

#### Scenario: Resolução Correta de Caminho Base do Visualizador
- **WHEN** o componente de edição de Markdown é instanciado para um croqui
- **THEN** o visualizador rico SHALL ter seu `baseUrl` apontando para o diretório do croqui atual, permitindo o carregamento de imagens locais referenciadas em `imagens/`.

### Requirement: Renderização de Booleanos Tri-State
O sistema SHALL renderizar campos booleanos como um `QComboBox` contendo 3 opções: Indefinido/Não informado (índice 0), Sim/Verdadeiro (índice 1) e Não/Falso (índice 2).
- **Customização**: O sistema SHALL extrair os rótulos de cada opção das opções do campo no Protobuf (`booleano_texto_indefinido`, `booleano_texto_sim`, `booleano_texto_nao`) ou usar textos padrão ("Não informado", "Sim", "Não").
- **Presença**: A seleção de "Não informado" SHALL executar `ClearField` no Protobuf, enquanto "Sim" define `True` e "Não" define `False`.

#### Scenario: Seleção de Opção Booleana Não Informado
- **WHEN** o usuário seleciona a opção "Não informado" em um campo booleano
- **THEN** o sistema SHALL limpar a presença do campo no Protobuf (`ClearField`).

#### Scenario: Seleção de Opção Booleana Sim ou Não
- **WHEN** o usuário seleciona "Sim" ou "Não" no dropdown booleano
- **THEN** o sistema SHALL atribuir respectivamente `True` ou `False` ao campo no Protobuf.

### Requirement: Renderização Especializada de Números e Coordenadas
O sistema SHALL renderizar números de ponto flutuante e coordenadas como `QLineEdit` com validação numérica, e inteiros como `QSpinBox` com suporte a estado nulo.
- **Ponto Flutuante**: O campo `QLineEdit` SHALL permitir entrada livre de casas decimais e manter o campo ausente quando vazio.
- **Inteiros**: O `QSpinBox` SHALL suportar um estado "Não definido" para campos ausentes e gravar explicitamente o valor quando definido como `0` ou superior.
- **Submensagens Inline de Coordenada**: O formulário SHALL exibir Latitude e Longitude; se ambos estiverem vazios, a submensagem de Coordenada SHALL ser limpa (`ClearField`).

#### Scenario: Edição de Coordenada GPS
- **WHEN** o usuário preenche a Latitude e Longitude de um campo de coordenada
- **THEN** o sistema SHALL instanciar e atualizar a submensagem `Coordenada` correspondente.

#### Scenario: Limpeza de Coordenada GPS
- **WHEN** o usuário apaga ambos os valores de Latitude e Longitude
- **THEN** o sistema SHALL executar `ClearField` da submensagem de coordenada pai.

### Requirement: Cartões de Ação para Sub-elementos no Rodapé do Formulário
O sistema SHALL renderizar seções/cartões contextuais no rodapé da visualização de formulário para mensagens que possuem coleções repetidas de sub-elementos exibidos na árvore (ex: `Croqui`, `Pico`, `Grupo`, `Setor`, `ViaMultiplasEnfiadas`).
- Cada cartão SHALL exibir o título da coleção, a contagem atual de itens cadastrados e um botão de ação rápida para adicionar um novo item.
- Ao clicar no botão de adição do cartão, o sistema SHALL acionar a criação do novo elemento na coleção da mensagem atual através do histórico de Undo/Redo (`QUndoCommand`), atualizar a árvore de dados e selecionar o novo elemento para edição.

#### Scenario: Visualização do Cartão de Sub-elementos
- **WHEN** o formulário de uma mensagem que contém coleções filhas na árvore (ex: `Pico`) é carregado
- **THEN** o sistema SHALL renderizar no rodapé do formulário um cartão para cada coleção (ex: "Setores e Grupos"), contendo a contagem de itens e o botão de adição correspondente.

#### Scenario: Adição Rápida de Sub-elemento via Cartão do Formulário
- **WHEN** o usuário clica no botão de adicionar em um cartão de sub-elementos no formulário
- **THEN** o sistema SHALL empilhar a adição no histórico de Undo/Redo, criar o novo item na coleção da mensagem pai, refletir a alteração na árvore e focar no formulário do novo item criado.

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

### Requirement: Renderização Direta de Card Visual para Mapas em Coleções Repetidas
O sistema SHALL renderizar itens de coleções repetidas do tipo `Mapa` (ou com anotação `mensagem_formato_na_ui = MAPA`) diretamente como cartões visuais abertos, sem encapsulamento em accordion colapsável (`WidgetColapsavel`).
- **Barra de Controle Superior**: Cada cartão SHALL exibir no topo uma alça de arraste `⠿`, o título composto pelo índice e nome do arquivo da foto (ex: `Mapa [0] - setor_fugitivos_p0.webp`), os botões de ação rápida `▲` (Subir) e `▼` (Descer), e o botão `Remover`.
- **Corpo Visual**: Cada cartão SHALL exibir uma miniatura com proporção preservada da imagem (`caminho_imagem_mapa`), as dimensões em pixels (`largura_mapa × altura_mapa`), o caminho relativo do arquivo e o botão de ação `Abrir no Editor de Mapas`.
- **Tratamento de Imagem Ausente**: Caso o arquivo da imagem não exista ou não possa ser lido, o cartão SHALL exibir um indicador visual de imagem ausente/placeholder sem interromper o fluxo da interface.

#### Scenario: Visualização de cartão de mapa no formulário
- **WHEN** o formulário de uma mensagem contendo mapas (ex: setor ou pico) é exibido
- **THEN** cada item da coleção de mapas SHALL ser renderizado como um cartão aberto com sua foto em miniatura, metadados de resolução e botão para o editor de mapas, sem botão de colapso/expansão.

#### Scenario: Visualização de mapa sem arquivo de imagem
- **WHEN** um mapa cadastrado não possui arquivo de imagem disponível no disco ou na memória
- **THEN** o cartão correspondente SHALL exibir um marcador de "Sem Imagem" no espaço da miniatura e desabilitar ações que dependam da imagem física.

### Requirement: Atualização e Sincronização de Cards de Mapa na Reordenação
O sistema SHALL sincronizar os cartões visuais de mapas ao responder ao sinal de movimentação no modelo (`repeated_movido`).
- Os índices nos títulos dos cartões (`Mapa [i]`) SHALL ser atualizados para refletir a nova posição contígua.
- Os botões `▲` e `▼` SHALL ter seus estados recalculados (desabilitando `▲` no índice 0 e `▼` no último índice).
- O reposicionamento do cartão no layout SHALL preservar a miniatura carregada e os metadados do mapa.
- A operação de movimentação SHALL ser despachada via comando no histórico (`CmdMoverRepeated`), garantindo reversibilidade com Desfazer (Undo) e Refazer (Redo).

#### Scenario: Reordenação de cards de mapa por botões ou arraste
- **WHEN** o usuário move um cartão de mapa para outra posição via botão ou drag-and-drop
- **THEN** o cartão do mapa com sua respectiva miniatura e dados SHALL se mover para a nova posição no layout
- **AND** os índices e botões de limite de todos os cartões da coleção SHALL ser atualizados.

#### Scenario: Desfazer reordenação de card de mapa
- **WHEN** o usuário desfaz (Undo) uma movimentação de mapa
- **THEN** o cartão do mapa e sua miniatura SHALL retornar à posição anterior na listagem visual e no Protobuf.


