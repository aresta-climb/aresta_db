# editor-markdown-imagens Specification

## ADDED Requirements

### Requirement: Biblioteca de Regras de Imagens Markdown (Library-First)
O sistema SHALL fornecer uma biblioteca autossuficiente (`editor.core.imagens_markdown`) para regras de negócio de nomenclatura, sanitização, formatação de tags e processamento de imagens destinadas ao Markdown.
- **Sanitização de Nomes**: A biblioteca SHALL converter nomes brutos para formato `snake_case`, em caracteres minúsculos, sem acentos ou símbolos especiais, com extensão `.webp`.
- **Prevenção de Colisões**: Ao sugerir um nome para uma pasta de destino, a biblioteca SHALL verificar a existência de arquivos com o mesmo nome e adicionar sufixos numéricos sequenciais (`_1`, `_2`).
- **Nomenclatura de Capturas de Tela**: Para imagens provenientes da área de transferência, a biblioteca SHALL gerar nomes no formato `imagem_AAAAMMDD_HHMMSS.webp`.
- **Formatação de Tag**: A biblioteca SHALL gerar strings no formato `![<legenda>](imagens/<nome_arquivo>)`.
- **Compressão e Persistência**: A biblioteca SHALL aplicar a conversão de imagem em formato WebP com qualidade lossy 85 e limite de área de 4.194.304 pixels (`comprimir_imagem_para_bytes_webp`) antes de gravar no disco.

#### Scenario: Sanitização de Nome de Arquivo
- **WHEN** a função de sanitização recebe a string `"Foto do Setor Principal (Cópia).png"`
- **THEN** ela SHALL retornar `"foto_do_setor_principal_copia.webp"`.

#### Scenario: Incremento Numérico em Caso de Colisão
- **WHEN** a função de geração de nome padrão recebe um nome cujo arquivo já existe na pasta de destino
- **THEN** ela SHALL retornar o nome acrescido de um sufixo numérico que garanta a unicidade do novo arquivo.

#### Scenario: Formatação de Tag com e sem Legenda
- **WHEN** a função de formatação de tag recebe o arquivo `"setor_bloco.webp"` com a legenda `"Bloco Central"`
- **THEN** ela SHALL retornar `"![Bloco Central](imagens/setor_bloco.webp)"`.
- **WHEN** a função de formatação de tag recebe o arquivo `"setor_bloco.webp"` com a legenda vazia
- **THEN** ela SHALL retornar `"![](imagens/setor_bloco.webp)"`.

### Requirement: Diálogo de Inserção de Imagens no Markdown
O sistema SHALL fornecer um diálogo modal (`DialogoInserirImagemMarkdown`) para auxiliar a seleção, importação e inserção de imagens em campos Markdown do editor.
- **Inserção Formatada**: Ao confirmar a seleção ou importação de uma imagem, o sistema SHALL inserir no editor a tag `![<Legenda>](imagens/<nome_arquivo>)` na posição atual do cursor (ou substituir o texto selecionado).
- **Legenda Obrigatória**: O diálogo SHALL conter um campo obrigatório para texto alternativo/legenda da imagem (`input_legenda`). O botão de inserção SHALL permanecer desabilitado enquanto a legenda não estiver preenchida.

#### Scenario: Inserção de Imagem com Legenda
- **WHEN** o usuário seleciona uma imagem e preenche a legenda "Vista Frontal" no diálogo
- **THEN** o sistema SHALL habilitar o botão de inserção e inserir `![Vista Frontal](imagens/nome_da_imagem.webp)` no editor de Markdown.

#### Scenario: Tentativa de Inserção sem Legenda
- **WHEN** o usuário seleciona uma imagem mas deixa o campo de legenda em branco
- **THEN** o botão de inserção SHALL permanecer desabilitado e a confirmação SHALL exibir aviso solicitando o preenchimento da legenda.

### Requirement: Galeria de Imagens do Croqui Atual
O diálogo SHALL listar todas as imagens disponíveis na pasta `imagens/` do croqui atual com pré-visualização de miniaturas e busca rápida.
- **Visualização em Grade**: Cada imagem da pasta `imagens/` SHALL ser representada com sua miniatura e nome de arquivo.
- **Filtro Textual**: O diálogo SHALL fornecer um campo de busca para filtrar dinamicamente a lista de imagens pelo nome do arquivo.

#### Scenario: Filtragem de Imagens na Galeria
- **WHEN** o usuário digita um termo no campo de busca do diálogo
- **THEN** a galeria SHALL exibir apenas as imagens cujo nome do arquivo contenha o termo digitado.

### Requirement: Importação e Otimização de Imagens
O sistema SHALL permitir importar novas imagens a partir do computador ou área de transferência, convertendo-as e otimizando-as automaticamente para o padrão do projeto.
- **Formatos Aceitos**: O importador SHALL aceitar arquivos nos formatos `.webp`, `.png`, `.jpg`, `.jpeg` e `.bmp`, além de imagens contidas na área de transferência (clipboard).
- **Parâmetros de Compressão**: As imagens importadas SHALL ser processadas com formato WebP, qualidade de compressão lossy `quality=85` e limitação de área máxima de 4 Megapixels (`max_area=4194304`), preservando a proporção de aspecto.
- **Destino do Arquivo**: O arquivo WebP resultante SHALL ser salvo diretamente na subpasta `imagens/` do croqui atual.

#### Scenario: Importação e Conversão de Imagem PNG Externa
- **WHEN** o usuário seleciona um arquivo `.png` de alta resolução de fora do projeto
- **THEN** o sistema SHALL redimensionar a imagem para caber em 4kk pixels (se necessário), compactar em WebP com qualidade 85 e salvá-la em `imagens/<nome>.webp`.

### Requirement: Interações Ágeis no Editor Markdown e Registro no Histórico (Undo/Redo)
O editor Markdown (`WidgetEditorMarkdown`) SHALL oferecer múltiplos pontos de entrada para inserção rápida de imagens e registrar as modificações de texto na pilha de histórico (`QUndoStack`).
- **Botão na Interface**: O editor SHALL exibir um botão de ação "Inserir Imagem" no cabeçalho do painel de edição.
- **Arrastar e Soltar (Drag & Drop)**: Ao arrastar uma imagem externa para o editor, o sistema SHALL abrir o diálogo de importação com a imagem pré-carregada; ao arrastar uma imagem já existente da pasta `imagens/`, o sistema SHALL inserir diretamente a tag Markdown no ponto de soltura.
- **Colar da Área de Transferência (`Ctrl+V`)**: Ao acionar colar com uma imagem no clipboard, o sistema SHALL abrir o diálogo de importação rápida com a captura pré-carregada.
- **Autocompletar Inline**: Ao digitar `![` ou `(imagens/` no editor de texto, o sistema SHALL exibir uma lista suspensa com os nomes das imagens existentes na pasta `imagens/` para autocompletar.
- **Histórico Global**: A inserção da tag de imagem no texto SHALL disparar a alteração através do controlador do formulário (`controller.alterar_primitivo`), permitindo que a ação seja desfeita (`Ctrl+Z`) e refeita (`Ctrl+Y`) de forma sincronizada com o modelo.

#### Scenario: Colar Imagem da Área de Transferência
- **WHEN** o usuário copia uma captura de tela para a área de transferência e pressiona Ctrl+V no editor Markdown
- **THEN** o sistema SHALL abrir o diálogo de importação com a captura de tela carregada e nome sugerido preenchido.

#### Scenario: Autocompletar Nome de Imagem Existente
- **WHEN** o usuário digita `(imagens/` no editor Markdown
- **THEN** o sistema SHALL exibir a lista de arquivos disponíveis na pasta `imagens/` para seleção rápida via teclado.

#### Scenario: Desfazer Inserção de Imagem
- **WHEN** o usuário insere uma imagem no Markdown e aciona a ação de Desfazer (Undo)
- **THEN** o sistema SHALL reverter o texto do editor para o estado anterior à inserção da imagem.
