# editor-dados-formularios Specification

## Purpose
TBD - created by archiving change editor-dados. Update Purpose after archive.
## Requirements
### Requirement: Geração Dinâmica de Formulários
O sistema SHALL criar e exibir formulários na área de edição principal contendo TODOS os campos da mensagem selecionada atualmente na árvore (exceto os marcados como invisíveis).
- **Cards de Campo**: Cada campo (primitivo ou sub-mensagem) SHALL ser renderizado dentro de um container do tipo Card (`QFrame` com borda fina e cantos arredondados) para demarcação visual clara.
- **Botões de Presença Contextuais**: Os botões para gerenciar a presença do campo (Adicionar/Remover) SHALL estar posicionados no canto superior direito de cada Card de campo correspondente.
- **Constrição de Largura**: Controles de edição primitivos curtos (números, strings curtas, combos, caixas de seleção) SHALL ter uma largura máxima configurada (ex: `150px` para números, `450px` para strings curtas) para evitar estiramento horizontal excessivo.
- **Ocultação de Campos Invisíveis**: Campos que possuam a opção de campo `formato_na_ui = INVISIVEL` no protobuf SHALL ser omitidos e não renderizados no formulário.

#### Scenario: Visualização de Campo Primitivo com Largura Constrita
- **WHEN** um campo primitivo (número ou string curta) é exibido no formulário
- **THEN** o controle de entrada correspondente SHALL respeitar o limite máximo de largura, não ocupando toda a extensão horizontal da tela.

#### Scenario: Ocultação de Campo com formato_na_ui Invisível
- **WHEN** o formulário é gerado para uma mensagem contendo campos anotados como `[(aresta.formato_na_ui) = INVISIVEL]`
- **THEN** o sistema SHALL pular a renderização desses campos, deixando-os ocultos ao usuário.

#### Scenario: Posicionamento do Botão de Presença no Card
- **WHEN** um campo opcional ou sub-mensagem com presença controlada é renderizado no card
- **THEN** o botão de "Adicionar" (caso ausente) ou "Remover" (caso presente) SHALL ser exibido no canto superior direito do card do campo.

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
- **Caminhos de Imagens**: O sistema SHALL resolver caminhos de imagem relativos presentes no markdown (ex: `imagens/...`) a partir do diretório `database/` do croqui atual.
- **Dimensionamento Responsivo**: O sistema SHALL redimensionar dinamicamente as imagens exibidas para que caibam perfeitamente na largura do painel do visualizador (sem ultrapassar a largura disponível e sem criar barras de rolagem horizontais).

#### Scenario: Dimensionamento de Imagem no Visualizador
- **WHEN** o visualizador rico renderiza o markdown ou sofre um redimensionamento de janela
- **THEN** o sistema SHALL ajustar proporcionalmente as dimensões de cada imagem (`QTextImageFormat`) para caber na largura livre do viewport.

