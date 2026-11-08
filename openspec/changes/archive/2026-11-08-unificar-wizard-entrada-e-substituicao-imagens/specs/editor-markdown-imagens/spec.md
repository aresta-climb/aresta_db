## MODIFIED Requirements

### Requirement: Diálogo de Inserção de Imagens no Markdown
O sistema SHALL fornecer um diálogo modal (`DialogoInserirImagemMarkdown`) baseado no wizard unificado de duas abas para auxiliar a seleção, recorte interativo, importação e inserção de imagens em campos Markdown do editor.
- **Inserção Formatada**: Ao confirmar a seleção ou importação de uma imagem, o sistema SHALL inserir no editor a tag `![<Legenda>](imagens/<nome_arquivo>)` na posição atual do cursor (ou substituir o texto selecionado).
- **Legenda Obrigatória**: O diálogo SHALL conter um campo obrigatório para texto alternativo/legenda da imagem (`input_legenda`). O botão de inserção SHALL permanecer desabilitado enquanto a legenda não estiver preenchida.
- **Interface Unificada com Recorte Interativo**: A aba `"Importar Nova Imagem"` SHALL apresentar botão de seleção de arquivo no cabeçalho (`"Selecionar Imagem..."`), área central de Drag & Drop (`AreaDropImagem`) com preview integrado e seleção elástica de recorte (*rubber-band crop*), barra de ferramentas de recorte (`✂ Recortar Área Selecionada` e `↺ Reverter Imagem Original`), painel informativo de metadados ricos (dimensões em pixels, peso original e comprimido em WebP), campo de nome de arquivo de destino com sanitização automática (`snake_case` com extensão `.webp`) e validação contínua de colisões contra arquivos existentes no disco e na memória RAM.
- **Validação de Colisões e Bloqueio**: Caso o nome do arquivo colida com imagem já existente e não renomeada, o sistema SHALL exibir aviso em vermelho e bloquear o botão de inserção até a resolução da duplicidade.

#### Scenario: Inserção de Imagem com Legenda
- **WHEN** o usuário seleciona uma imagem e preenche a legenda `"Vista Frontal"` no diálogo
- **THEN** o sistema SHALL habilitar o botão de inserção e inserir `![Vista Frontal](imagens/nome_da_imagem.webp)` no editor de Markdown

#### Scenario: Tentativa de Inserção sem Legenda
- **WHEN** o usuário seleciona uma imagem mas deixa o campo de legenda em branco
- **THEN** o botão de inserção SHALL permanecer desabilitado e a confirmação SHALL exibir aviso solicitando o preenchimento da legenda

#### Scenario: Unificação de Layout e Feedback de Colisão em Tempo Real
- **WHEN** o usuário abre o diálogo para importar uma nova imagem
- **THEN** a interface exibe área de drag & drop, barra de recorte interativo (`✂ Recortar Área Selecionada` e `↺ Reverter Imagem Original`), botão de cabeçalho `"Selecionar Imagem..."`, painel de metadados da imagem selecionada e campo de slug com feedback de validação em tempo real

#### Scenario: Recorte Interativo de Imagem antes da Inserção no Markdown
- **WHEN** o usuário importa uma imagem na aba `"Importar Nova Imagem"`, seleciona uma sub-região retangular no preview e aciona `"✂ Recortar Área Selecionada"`
- **THEN** o sistema SHALL recortar a imagem, reprocessar os bytes WebP e atualizar os metadados de resolução e tamanho antes de inserir a imagem no Markdown, permitindo também restaurar a imagem original via `"↺ Reverter Imagem Original"`
