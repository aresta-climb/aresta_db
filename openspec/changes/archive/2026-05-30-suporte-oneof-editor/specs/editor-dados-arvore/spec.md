## MODIFIED Requirements

### Requirement: Exibição da Árvore de Dados do Croqui
O sistema SHALL exibir uma visão em formato de árvore listando hierarquicamente apenas as sub-mensagens contidas no `croqui.proto` que forem anotadas com a message option `MensagemFormatoUi.SEPARADO` ou `MensagemFormatoUi.ONEOF`. Outros campos escalares ou mensagens que não correspondam a essas opções não devem aparecer na árvore.
Para campos repetidos (`repeated`) dessas mensagens, a árvore deve apresentar um nó agrupador ("expando"), que ao ser expandido exibe os elementos da lista sequencialmente.
O rótulo do nó na árvore SHALL ser derivado do campo anotado com `titulo_na_ui` da mensagem, se presente e não vazio, caindo de volta para o campo `nome` ou o rótulo padrão da mensagem.

#### Scenario: Carregamento Inicial da Árvore
- **WHEN** a página de Editor de Dados é aberta
- **THEN** o sistema SHALL renderizar um `QTreeView` contendo apenas as mensagens/sub-mensagens anotadas com `MensagemFormatoUi.SEPARADO` ou `MensagemFormatoUi.ONEOF`, com o `Croqui` como raiz invisível ou implícita.

#### Scenario: Campos Repetidos como Expandos
- **WHEN** uma mensagem possui um campo do tipo `repeated` que contém mensagens `SEPARADO` ou `ONEOF`
- **THEN** a árvore SHALL renderizar um nó agrupador intermediário (expando) para o campo repetido, e listar cada item da coleção logo abaixo dele.

#### Scenario: Seleção de uma Mensagem na Árvore
- **WHEN** o usuário seleciona um nó de mensagem na árvore (seja nó comum ou item de um campo repetido)
- **THEN** o sistema SHALL carregar a visão completa de formulário daquela mensagem específica na área direita.

#### Scenario: Rótulo de Nó Baseado em titulo_na_ui
- **WHEN** um nó de mensagem é exibido na árvore do editor e a mensagem correspondente tem um campo anotado com `[(aresta.titulo_na_ui) = true]`
- **THEN** o sistema SHALL usar o valor desse campo como rótulo na árvore do editor (ou o nome do tipo/rótulo padrão se estiver vazio).

#### Scenario: Rótulo de ArquivoMarkdown Baseado no Título do Conteúdo ou Nome do Arquivo
- **WHEN** um nó de `ArquivoMarkdown` é exibido na árvore do editor
- **THEN** o sistema SHALL primeiro tentar extrair o primeiro cabeçalho H1 (texto iniciado com `#`) do conteúdo do markdown. Se não for encontrado ou não estiver carregado, o sistema SHALL usar o nome do arquivo (sem extensão e formatado de forma amigável) como rótulo na árvore.


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
