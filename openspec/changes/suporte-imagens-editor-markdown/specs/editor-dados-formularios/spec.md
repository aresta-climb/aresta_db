# Delta: editor-dados-formularios

## MODIFIED Requirements

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
