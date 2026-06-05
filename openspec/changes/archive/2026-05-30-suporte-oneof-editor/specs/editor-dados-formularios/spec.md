## ADDED Requirements

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
