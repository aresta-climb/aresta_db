## ADDED Requirements

### Requirement: Substituição de Imagem no Editor de Imagens em Memória RAM
O sistema SHALL permitir a substituição do conteúdo de uma imagem existente selecionada no Editor de Imagens por um novo arquivo selecionado no disco, aplicando pré-processamento e compressão WebP automáticos em memória RAM e suportando desfazer/refazer (`QUndoCommand`) no histórico global de operações.

#### Scenario: Substituição de Imagem com Pré-processamento e Recarregamento em RAM
- **WHEN** o usuário seleciona uma imagem na lista do Editor de Imagens e aciona a ação "Substituir Imagem..." escolhendo um novo arquivo de imagem
- **THEN** o sistema SHALL processar e converter a nova imagem para WebP, gravar a imagem atualizada no buffer de memória RAM do `CroquiModel` via `QUndoCommand`, recarregar o visualizador e a lista, e emitir o sinal de alteração para as demais telas.

### Requirement: Sincronização Reativa Global do Editor de Imagens
O sistema SHALL sincronizar automaticamente a lista de imagens e a imagem atualmente aberta no visualizador do Editor de Imagens quando qualquer imagem for alterada, adicionada ou removida em outra área (Editor de Mapas ou Editor de Dados).

#### Scenario: Atualização Automática ao Alterar Imagem no Editor de Mapas
- **WHEN** uma imagem for substituída no Editor de Mapas ou no formulário de dados
- **THEN** o Editor de Imagens SHALL detectar o sinal `imagem_alterada`, recarregar a visualização da imagem correspondente a partir da memória RAM e atualizar sua miniatura na lista.
