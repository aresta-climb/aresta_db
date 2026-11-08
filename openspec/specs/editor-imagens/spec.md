## Purpose
Define os requisitos e o comportamento do editor de imagens integrado do Editor Aresta.
## Requirements
### Requirement: Integração do Editor de Imagens
O sistema SHALL fornecer um editor de imagens integrado para processamento em lote (crop, rotação e máscaras), acessível de forma isolada ou embutido na área principal quando acionado via a visão de árvore de dados.

#### Scenario: Acesso Embutido na Árvore de Dados
- **WHEN** o usuário seleciona um nó correspondente a uma imagem na árvore do Editor de Dados
- **THEN** o sistema SHALL exibir o widget de edição de imagens (`WidgetEditorImagens`) na parte direita da área central focando exclusivamente na edição daquela imagem selecionada.

#### Scenario: Listagem de Imagens
- **WHEN** o editor de imagens é carregado em modo autônomo ou via barra lateral "Imagens"
- **THEN** o sistema SHALL listar todas as imagens presentes na pasta `imagens/` do croqui atual.

### Requirement: Substituição de Imagem no Editor de Imagens em Memória RAM
O sistema SHALL permitir a substituição do conteúdo de uma imagem existente selecionada no Editor de Imagens através do wizard unificado de duas abas (`"Importar Nova Imagem"` com Drag & Drop, preview, recorte interativo e metadados ricos, e `"Imagens do Croqui"` com galeria em disco e RAM) em modo de destino fixo, aplicando pré-processamento e compressão WebP automáticos em memória RAM e suportando desfazer/refazer (`CmdAlterarImagem`) no histórico global de operações.

#### Scenario: Substituição de Imagem com Pré-processamento e Recarregamento em RAM
- **WHEN** o usuário seleciona uma imagem na lista do Editor de Imagens e aciona a ação `"Substituir Imagem..."`, confirmando uma nova imagem (com ou sem recorte) ou uma imagem da galeria no wizard unificado
- **THEN** o sistema SHALL gravar os bytes WebP atualizados sob o caminho da imagem selecionada no buffer de memória RAM do `CroquiModel` via comando de histórico, recarregar o visualizador e a lista e emitir o sinal `imagem_alterada` para as demais telas

### Requirement: Sincronização Reativa Global do Editor de Imagens
O sistema SHALL sincronizar automaticamente a lista de imagens e a imagem atualmente aberta no visualizador do Editor de Imagens quando qualquer imagem for alterada, adicionada ou removida em outra área (Editor de Mapas ou Editor de Dados).

#### Scenario: Atualização Automática ao Alterar Imagem no Editor de Mapas
- **WHEN** uma imagem for substituída no Editor de Mapas ou no formulário de dados
- **THEN** o Editor de Imagens SHALL detectar o sinal `imagem_alterada`, recarregar a visualização da imagem correspondente a partir da memória RAM e atualizar sua miniatura na lista.
