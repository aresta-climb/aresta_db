## MODIFIED Requirements

### Requirement: Substituição de Imagem no Editor de Imagens em Memória RAM
O sistema SHALL permitir a substituição do conteúdo de uma imagem existente selecionada no Editor de Imagens através do wizard unificado de duas abas (`"Importar Nova Imagem"` com Drag & Drop, preview, recorte interativo e metadados ricos, e `"Imagens do Croqui"` com galeria em disco e RAM) em modo de destino fixo, aplicando pré-processamento e compressão WebP automáticos em memória RAM e suportando desfazer/refazer (`CmdAlterarImagem`) no histórico global de operações.

#### Scenario: Substituição de Imagem com Pré-processamento e Recarregamento em RAM
- **WHEN** o usuário seleciona uma imagem na lista do Editor de Imagens e aciona a ação `"Substituir Imagem..."`, confirmando uma nova imagem (com ou sem recorte) ou uma imagem da galeria no wizard unificado
- **THEN** o sistema SHALL gravar os bytes WebP atualizados sob o caminho da imagem selecionada no buffer de memória RAM do `CroquiModel` via comando de histórico, recarregar o visualizador e a lista e emitir o sinal `imagem_alterada` para as demais telas
