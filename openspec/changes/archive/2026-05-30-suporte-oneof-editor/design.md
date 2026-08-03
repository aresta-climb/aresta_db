## Context

Atualmente, o Editor Aresta possui regras específicas acopladas para tratar wrappers de arquivo e sub-elementos com `oneof` (ex. `SetorOuGrupo`, `ArquivoSetor`, `ArquivoGrupo`, `ArquivoMarkdown`). Com a atualização do `croqui.proto`, o enum de formato `ONEOF_CONTEUDO` foi substituído pelo formato mais abrangente `ONEOF`, e novas opções customizadas de campo como `oneof_default` e `titulo_na_ui` foram adicionadas para flexibilizar a interface. O editor precisa ser adaptado de forma genérica para suportar estas novas regras.

## Goals / Non-Goals

**Goals:**
- Substituir o tratamento de mensagens `ONEOF_CONTEUDO` pelo formato genérico `ONEOF`.
- Implementar transparência de união recursiva em `_resolve_transparency` para mensagens configuradas como `ONEOF`.
- Suportar a propriedade `titulo_na_ui` de forma dinâmica na árvore do editor de dados (`ProtobufTreeModel`), de forma que o nó exiba o valor do campo marcado.
- Ao criar um elemento contendo um `oneof` na interface, inicializar o campo anotado com `oneof_default` por padrão. Caso contrário, permitir ao usuário escolher.
- Carregar e persistir de forma recursiva arquivos markdown `.md` externos contendo propriedades estruturadas como YAML frontmatter e descrição textual no corpo do arquivo.
- Permitir a edição do nome do arquivo externo na interface do formulário e gerenciar a renomeação e exclusão física no disco.
- Renderizar markdown rico em um componente split-pane side-by-side e redimensionar dinamicamente as imagens para caber no painel de pré-visualização.

**Non-Goals:**
- Mudar a lógica de compilação externa de croquis feita pela ferramenta de deploy.
- Implementar modificações em outros formatos de mensagens (como `SEPARADO` ou `INLINE`) além das marcadas como `ONEOF`.

## Decisions

### 1. Generalização da Resolução de Transparência (`ONEOF`)
- **Decisão**: Alterar `ProtobufNode._resolve_transparency` para verificar se `msg.DESCRIPTOR` tem a opção `mensagem_formato_na_ui` com o valor `ONEOF`. Se sim, obter o campo ativo do `oneof`. Se este campo ativo contiver uma sub-mensagem, resolver recursivamente. Caso contrário (campos escalares ou vazios), retornar o próprio wrapper.
- **Alternativa considerada**: Manter condicionais explícitas baseadas no nome das classes. **Rejeitada** pois novos wrappers teriam que ser adicionados manualmente e o acoplamento continuaria alto.

### 2. Determinação de Rótulos de Nós Baseada em `titulo_na_ui`
- **Decisão**: Em `ProtobufTreeModel.data()`, para qualquer nó de mensagem que não seja a raiz ou agrupador, inspecionar a definição da mensagem em busca de campos que tenham a extensão `titulo_na_ui` configurada como `True`. Se houver e o campo estiver preenchido, exibir seu valor. Caso contrário, tentar cair de volta no campo `nome`, depois em heurísticas específicas de `ArquivoMarkdown`, e finalmente no rótulo padrão do descriptor/tipo.
- **Justificativa**: Permite que os analistas e editores de croquis rotulem qualquer mensagem livremente na árvore configurando a anotação no arquivo `.proto`.

### 3. Inicialização e Criação Automática Baseada em `oneof_default`
- **Decisão**: No formulário e na árvore, se o usuário solicitar a criação de um elemento contendo `oneof`, inspecionaremos as propriedades dos campos contidos nesse `oneof`.
  - Se um campo estiver marcado com `[(aresta.oneof_default) = true]`, ele será criado e inicializado automaticamente.
  - Se nenhum campo do `oneof` tiver essa anotação, exibiremos um diálogo (`QInputDialog` ou diálogo simples customizado) permitindo a seleção da opção antes de prosseguir com a inserção.

### 4. Salvamento e Carregamento de Arquivos Externos (.md)
- **Decisão**: Ajustar o carregamento para ler recursivamente os arquivos `.md` externos na pasta `database/`. O carregamento decodificará o frontmatter YAML (seção inicial cercada por `---`) e o converterá em sub-protos estruturados, enquanto o corpo do arquivo será atribuído à `descricao` ou `conteudo`.
- **Rastreamento Estável**: Manter uma lista de referências de mensagens (`self.referencias_mensagens`) em `JanelaPrincipal` para garantir que o Garbage Collector não destrua os objetos de dados em memória, estabilizando seus IDs numéricos em Python (`id(mensagem)`), que são mapeados para os arquivos físicos nos dicionários `self.arquivos_carregados` e `self.caminhos_originais`.
- **Salvamento Atomizado**: O salvamento criará uma cópia profunda (deep copy) do croqui antes de extrair os dados. Isso previne que os dados de conteúdo em memória ativos na UI sejam limpos ou mutados durante a escrita dos arquivos físicos. O salvamento persistirá o formato correto de `.md` (YAML frontmatter + corpo) e apagará os arquivos antigos que foram renomeados na UI.

### 5. Campo de Nome de Arquivo na Interface do Formulário
- **Decisão**: Em `WidgetFormularioPadrao.load_node`, se o nó atual corresponder a uma sub-mensagem salva externamente, injetar um campo de entrada do tipo `QLineEdit` rotulado "Nome do arquivo:" no topo do layout do formulário. Mudanças no texto desse campo atualizam o mapeamento de arquivos em tempo real. Ao adicionar novos elementos, o editor deduzirá e gerará automaticamente um nome de arquivo legível e único (ex: `setor_nome.md`) e registrará o mapeamento.

### 6. Componente Split-Pane para Edição de Markdown Rico
- **Decisão**: Implementar `WidgetEditorMarkdown` que renderiza o editor side-by-side:
  - Lado esquerdo: `QTextEdit` para entrada em texto puro com fonte monoespaçada.
  - Lado direito: Visualizador rico `AutoScalingTextBrowser` que herda de `QTextBrowser`.
- **Visualizador customizado (`AutoScalingTextBrowser`)**: O motor de rich text nativo do Qt6 renderiza o markdown via `setMarkdown()`, mas carece de suporte a CSS `max-width` para responsividade de imagens. No método `scale_images()`, iteramos pelas imagens do documento, recuperamos o tamanho original (via cache de recursos ou abrindo de forma relativa com `baseUrl`), e calculamos a escala proporcional baseada na largura atual do viewport do widget. O ajuste físico da largura e altura é aplicado via `QTextImageFormat` usando um cursor de edição de documento. A re-escala é disparada automaticamente no `resizeEvent` e sempre que o Markdown é alterado.

## Risks / Trade-offs

- **[Risco]** Mensagem `ArquivoMarkdown` agora não tem mais a propriedade `titulo`.
  - **Mitigação**: O nome exibido na árvore para as `secoes_textuais` (de tipo `ArquivoMarkdown`) passará a ser extraído do primeiro cabeçalho H1 (linha iniciada com `#`) do conteúdo do markdown. Caso não seja encontrado ou não esteja carregado, o nome do arquivo em `caminho` (ex: `introducao.md` -> `Introdução`) será usado como fallback. Ao salvar, a geração de nome de arquivo também usará um índice sequencial ou deduzirá a partir de outro campo para evitar colisões.
- **[Risco]** A re-escala constante de imagens no visualizador rich text em tempo de redimensionamento pode introduzir latência.
  - **Mitigação**: O carregamento de imagens do disco é mitigado cacheando os objetos `QImage` no cache de recursos do `QTextDocument` (`doc.addResource`). Consultas subsequentes recuperam o tamanho instantaneamente sem I/O de disco.
- **[Risco]** Cópia profunda no salvamento aumenta o overhead de processamento para grandes croquis.
  - **Mitigação**: O tamanho das mensagens do croqui é relativamente pequeno em termos de uso de memória em RAM. O isolamento de estado obtido com a cópia profunda supera amplamente o overhead de clonagem, eliminando bugs de UI vazia após salvamento.
