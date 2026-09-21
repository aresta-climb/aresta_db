## ADDED Requirements

### Requirement: Preservação de Imagens Markdown na Limpeza de Arquivos no Salvamento
O sistema SHALL identificar e preservar todas as imagens referenciadas via tags Markdown (`![]()`) durante o ciclo de salvamento, compilação e higienização do banco de dados (`limpar_arquivos_nao_utilizados` / `coletar_referencias_arquivos`).
- **Varredura Completa de Campos de Texto**: A rotina de coleta de referências SHALL inspecionar recursivamente e extrair nomes de imagens presentes em `croqui.descricao`, `pico.descricao`, em todas as escaladas filhas (`via_esportiva.descricao`, `via_movel.descricao`, `boulder.descricao`, `via_multiplas_enfiadas.descricao`, `highline.descricao`), em `trilha.descricao` e em `ponto_de_interesse.descricao`.
- **Prevenção de Exclusão Indevida**: Nenhuma imagem referenciada em campos Markdown válidos do croqui SHALL ser excluída (`unlink`) pelo limpador de arquivos órfãos.

#### Scenario: Preservação de Imagem em Descrição de Croqui ou Pico ao Salvar
- **WHEN** o usuário insere uma imagem na descrição do croqui ou na descrição de um pico e executa o salvamento
- **THEN** a rotina de limpeza de arquivos NÃO SHALL excluir o arquivo WebP correspondente do disco, mantendo-o íntegro e detectável pelo controle de versão.

#### Scenario: Preservação de Imagem em Descrição de Vias e Trilhas
- **WHEN** uma imagem for referenciada na descrição de uma via esportiva, móvel, boulder, enfiada, highline ou trilha
- **THEN** o sistema SHALL computar o arquivo como referenciado na lista de arquivos ativos durante a higienização do banco de dados.

## MODIFIED Requirements

### Requirement: Diálogo de Inserção de Imagens no Markdown
O sistema SHALL fornecer um diálogo modal (`DialogoInserirImagemMarkdown`) para auxiliar a seleção, importação e inserção de imagens em campos Markdown do editor.
- **Inserção Formatada**: Ao confirmar a seleção ou importação de uma imagem, o sistema SHALL inserir no editor a tag `![<Legenda>](imagens/<nome_arquivo>)` na posição atual do cursor (ou substituir o texto selecionado).
- **Legenda Obrigatória**: O diálogo SHALL conter um campo obrigatório para texto alternativo/legenda da imagem (`input_legenda`). O botão de inserção SHALL permanecer desabilitado enquanto a legenda não estiver preenchida.
- **Interface Unificada de Seleção e Importação**: O diálogo SHALL apresentar a mesma estrutura visual e ergonômica do diálogo de mapas (`DialogoAdicionarMapa`), incluindo botão de ação de seleção de arquivo no cabeçalho ("Selecionar Imagem..."), área central de Drag & Drop (`AreaDropImagem`) com preview integrado após a escolha, painel informativo de metadados ricos (dimensões em pixels, peso original e comprimido em WebP), campo de nome de arquivo de destino com sanitização automática (`snake_case` com extensão `.webp`) e validação contínua de colisões com feedback em tempo real contra arquivos existentes no disco e na memória RAM.
- **Validação de Colisões e Bloqueio**: Caso o nome do arquivo colida com imagem já existente e não renomeada, o sistema SHALL exibir aviso em vermelho e bloquear o botão de inserção até a resolução da duplicidade.

#### Scenario: Inserção de Imagem com Legenda
- **WHEN** o usuário seleciona uma imagem e preenche a legenda "Vista Frontal" no diálogo
- **THEN** o sistema SHALL habilitar o botão de inserção e inserir `![Vista Frontal](imagens/nome_da_imagem.webp)` no editor de Markdown.

#### Scenario: Tentativa de Inserção sem Legenda
- **WHEN** o usuário seleciona uma imagem mas deixa o campo de legenda em branco
- **THEN** o botão de inserção SHALL permanecer desabilitado e a confirmação SHALL exibir aviso solicitando o preenchimento da legenda.

#### Scenario: Unificação de Layout e Feedback de Colisão em Tempo Real
- **WHEN** o usuário abre o diálogo para importar uma nova imagem
- **THEN** a interface exibe área de drag & drop, botão de cabeçalho "Selecionar Imagem...", painel de metadados da imagem selecionada e campo de slug com feedback de validação em tempo real.

### Requirement: Interações Ágeis no Editor Markdown e Registro no Histórico (Undo/Redo)
O editor Markdown (`WidgetEditorMarkdown`) SHALL oferecer múltiplos pontos de entrada para inserção rápida de imagens e registrar as modificações de texto na pilha de histórico (`QUndoStack`), garantindo digitação responsiva e sem congelamentos.
- **Botão na Interface**: O editor SHALL exibir um botão de ação "Inserir Imagem" no cabeçalho do painel de edição.
- **Arrastar e Soltar (Drag & Drop)**: Ao arrastar uma imagem externa para o editor, o sistema SHALL abrir o diálogo de importação com a imagem pré-carregada; ao arrastar uma imagem já existente da pasta `imagens/`, o sistema SHALL inserir diretamente a tag Markdown no ponto de soltura.
- **Colar da Área de Transferência (`Ctrl+V`)**: Ao acionar colar com uma imagem no clipboard, o sistema SHALL abrir o diálogo de importação rápida com a captura pré-carregada.
- **Autocompletar Inline**: Ao digitar `![` ou `(imagens/` no editor de texto, o sistema SHALL exibir uma lista suspensa com os nomes das imagens existentes na pasta `imagens/` para autocompletar.
- **Histórico Global e Gerenciamento Atômico de Imagens**: A inserção da tag de imagem no texto e a persistência dos bytes da imagem no modelo SHALL ser orquestrada através de comandos na pilha de histórico (`historico`), permitindo que a inclusão da tag e dos bytes seja desfeita (`Ctrl+Z`) e refeita (`Ctrl+Y`) de forma atômica e consistente com o Princípio VII.
- **Temporização de Coalescência na Digitação e Atualização**: O editor de texto Markdown SHALL aplicar uma biblioteca autossuficiente (`editor.core.temporizador_coalescencia.TemporizadorCoalescencia`) com atraso entre 200ms e 300ms na digitação, atualizando a pré-visualização renderizada e emitindo o comando para o modelo apenas quando o usuário pausar a digitação ou perder o foco do campo.
- **Prevenção de Duplo Render**: Ao receber notificação externa via `set_conteudo`, o editor SHALL comparar o conteúdo recebido com o texto atual e ignorar a re-renderização do preview e o re-escaneamento de imagens caso os textos sejam idênticos.

#### Scenario: Colar Imagem da Área de Transferência
- **WHEN** o usuário copia uma captura de tela para a área de transferência e pressiona Ctrl+V no editor Markdown
- **THEN** o sistema SHALL abrir o diálogo de importação com a captura de tela carregada e nome sugerido preenchido.

#### Scenario: Autocompletar Nome de Imagem Existente
- **WHEN** o usuário digita `(imagens/` no editor Markdown
- **THEN** o sistema SHALL exibir a lista de arquivos disponíveis na pasta `imagens/` para seleção rápida via teclado.

#### Scenario: Desfazer Inserção de Imagem
- **WHEN** o usuário insere uma imagem no Markdown e aciona a ação de Desfazer (Undo)
- **THEN** o sistema SHALL reverter o texto do editor para o estado anterior à inserção da imagem.

#### Scenario: Digitação Contínua com Coalescência no Preview e no Modelo
- **WHEN** o usuário digita múltiplos caracteres consecutivamente em intervalo menor que 200ms
- **THEN** o texto é exibido imediatamente no campo de edição e a atualização do preview e do modelo é postergada até que ocorra uma pausa de digitação.

#### Scenario: Prevenção de Duplo Render em Ciclo de Eco
- **WHEN** o editor Markdown recebe a confirmação de dado alterado via `set_conteudo` com o mesmo texto já digitado
- **THEN** o editor não deve invocar novamente a renderização Markdown nem o redimensionamento de imagens.
