## ADDED Requirements

### Requirement: Substituição de Imagem no Editor de Mapas em Memória RAM
O sistema SHALL permitir a substituição da imagem de fundo de um mapa existente por uma nova imagem estritamente em memória RAM com suporte a `QUndoCommand`, aplicando pré-processamento e compressão automática para WebP e recarregando a cena visual enquanto preserva a lista e geometrias de Pontos de Interesse (POIs).

#### Scenario: Substituição de Imagem Bem-Sucedida com Undo/Redo
- **WHEN** o usuário aciona a ação "Substituir Imagem..." no Editor de Mapas e escolhe um novo arquivo de imagem
- **THEN** o sistema SHALL pré-processar a imagem para WebP, atualizar o buffer em memória RAM através de um comando `QUndoCommand` e recarregar a imagem de fundo na cena preservando os POIs, permitindo desfazer e refazer a operação.

### Requirement: Sincronização Reativa Global do Mapa
O sistema SHALL sincronizar automaticamente a cena e a imagem de fundo do mapa quando os bytes da imagem forem alterados em qualquer outra visão (Editor de Imagens ou Editor de Dados).

#### Scenario: Atualização Automática ao Alterar Imagem no Editor de Imagens
- **WHEN** a imagem do mapa atual for substituída ou modificada no Editor de Imagens
- **THEN** o Editor de Mapas SHALL detectar o sinal `imagem_alterada` e recarregar a nova imagem de fundo da memória RAM sem desalinhar os POIs existentes.

### Requirement: Acesso Direto do Mapa ao Editor de Imagens
O sistema SHALL fornecer uma ação na barra de ferramentas do Editor de Mapas para abrir e focar a imagem do mapa atualmente selecionado dentro do Editor de Imagens.

#### Scenario: Foco da Imagem no Editor de Imagens
- **WHEN** o usuário clica no botão "Abrir no Editor de Imagens" no Editor de Mapas
- **THEN** o sistema SHALL comutar a visualização para a aba de Imagens da Janela Principal e selecionar o arquivo de imagem do mapa atual.

### Requirement: Diálogo Robusto de Adição de Mapas
O sistema SHALL fornecer um diálogo robusto para adição de novos mapas contendo botão explícito de seleção de arquivos, suporte a arrastar e soltar (drag & drop), painel de metadados ricos (dimensões, tamanho formatado e formato), pré-processamento WebP automático em RAM e validação de nomes e colisões em tempo real.

#### Scenario: Seleção de Arquivo com Exibição de Metadados e Pré-processamento
- **WHEN** o usuário seleciona ou arrasta um arquivo de imagem no diálogo de adição de mapa
- **THEN** o sistema SHALL exibir a pré-visualização gráfica, apresentar resolução ($W \times H$), tamanho e formato original nos metadados, e pré-processar os bytes para WebP.

#### Scenario: Validação de Conflito de Nomes em Tempo Real
- **WHEN** o usuário digita um nome de arquivo que já existe na memória RAM ou na pasta `imagens/` do disco
- **THEN** o sistema SHALL exibir um alerta visual imediato de colisão de nomes e desabilitar o botão de confirmação.
