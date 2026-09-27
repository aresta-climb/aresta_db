## ADDED Requirements

### Requirement: Agrupamento e Ocultação Progressiva de Campos Avançados
O sistema SHALL agrupar dinamicamente os campos marcados com a opção `avancado = true` no Protobuf dentro de uma seção colapsável ("Opções Avançadas") no final da lista de campos de cada formulário de entidade.

- **Identificação Declarativa**: O sistema SHALL inspecionar as opções de cada campo (`FieldDescriptor`) e identificar como avançado qualquer campo que contenha `(aresta.avancado) = true`.
- **Campos Principais**: Campos que não possuam `avancado = true` (incluindo `nome`, `dificuldade`, `extensao`, `conquistadores`, `data_abertura`, `destaque` e `descricao`) SHALL ser renderizados diretamente no layout principal do formulário.
- **Renderização Condicional do Expando**: Se uma mensagem não possuir nenhum campo marcado como avançado, a seção colapsável de avançados SHALL NÃO ser renderizada.
- **Rótulo Informativo de Preenchimento**: Quando colapsado, o cabeçalho do expando SHALL exibir a contagem total de campos avançados e, caso algum deles possua valor não-nulo/não-vazio no Protobuf, exibir a quantidade de campos preenchidos (ex: `▶ Opções Avançadas (X preenchidos de Y)` quando houver dados preenchidos, ou `▶ Opções Avançadas (Y campos)` quando todos estiverem vazios). Quando expandido, o rótulo SHALL exibir `▼ Ocultar Opções Avançadas`.
- **Persistência de Expansão na Sessão**: Ao expandir ou recolher a seção de campos avançados, o sistema SHALL memorizar o estado (aberto ou fechado) como preferência da sessão do editor. Ao navegar para qualquer outro elemento na árvore de dados durante a mesma sessão, o novo formulário exibido SHALL inicializar a seção de avançados respeitando o estado memorizado.
- **Sincronização com Undo/Redo e Modelo**: Todos os controles de edição pertencentes à seção de avançados SHALL manter as propriedades de mapeamento do Protobuf (`protobuf_field` e `protobuf_msg_id`), despachar alterações exclusivamente através do controlador e responder a atualizações de Undo/Redo e notificações de sinais do modelo de dados.

#### Scenario: Formulário de Mensagem sem Campos Avançados
- **WHEN** o usuário seleciona um nó na árvore cuja mensagem Protobuf não possui nenhum campo com a opção `(aresta.avancado) = true`
- **THEN** o sistema SHALL renderizar todos os campos visíveis normalmente e NÃO exibir o botão/expando de "Opções Avançadas".

#### Scenario: Visualização Inicial de Formulário com Campos Avançados Vazios
- **WHEN** o formulário de uma mensagem que contém campos avançados vazios (ex: nova `ViaEsportiva`) é exibido pela primeira vez
- **THEN** os campos principais (`nome`, `dificuldade`, `extensao`, `conquistadores`, `data_abertura`, `destaque`, `descricao`) SHALL estar visíveis diretamente
- **AND** a seção de campos avançados SHALL estar colapsada com o texto indicando o total de campos (ex: `▶ Opções Avançadas (N campos)`).

#### Scenario: Indicador de Campos Avançados Preenchidos
- **WHEN** uma mensagem possui 2 campos avançados preenchidos com valores não-padrão (ex: `dificuldade_artificial` e `chave_pix_manutencao`) e o expando está colapsado
- **THEN** o rótulo do expando SHALL exibir `▶ Opções Avançadas (2 preenchidos de N)`.

#### Scenario: Alternância de Visibilidade dos Campos Avançados
- **WHEN** o usuário clica no botão do expando de campos avançados colapsado
- **THEN** a área de conteúdo dos campos avançados SHALL tornar-se visível, exibindo os cards dos campos avançados para edição
- **AND** o rótulo do botão SHALL mudar para `▼ Ocultar Opções Avançadas`.

#### Scenario: Persistência do Estado de Expansão ao Navegar na Árvore
- **WHEN** o usuário expande a seção de campos avançados em uma via e em seguida seleciona outra via ou setor na árvore de dados
- **THEN** o formulário do novo item selecionado SHALL ser exibido com a seção de campos avançados já aberta automaticamente.

#### Scenario: Suporte a Undo e Redo em Campos Avançados
- **WHEN** o usuário edita um campo dentro da seção de opções avançadas e em seguida aciona a ação Desfazer (Undo)
- **THEN** o valor anterior do campo SHALL ser restaurado no widget e no Protobuf através do histórico global de comandos.
