## Why

O Editor de Mapas e o Editor de Imagens atualmente carecem de ferramentas intuitivas para substituir imagens existentes, navegar diretamente entre o mapa e o editor de imagens, e cadastrar novos mapas com pré-visualização, metadados claros e pré-processamento WebP automático.

Fundamentalmente, para garantir a consistência dos dados, a segurança contra perdas e a integridade de desfazer/refazer (Undo/Redo), todas as alterações de imagens e mapas devem operar estritamente em memória RAM (Shadow State no `CroquiModel`), sincronizando reativamente todas as telas abertas e despachando comandos `QUndoCommand` para a pilha global. A gravação física em disco ocorrerá exclusivamente no momento de salvar o croqui.

## What Changes

- **Operação 100% em Memória RAM (Shadow State) e QUndoCommand**:
  - Todas as adições, substituições e remoções de imagens e mapas ocorrem estritamente no buffer em memória do `CroquiModel` via comandos `QUndoCommand`. Nenhuma escrita em disco ocorre antes do salvamento explícito.
  - Sincronização reativa universal: ao alterar uma imagem em qualquer lugar (Editor de Dados, Editor de Mapas ou Editor de Imagens), todas as outras visões sincronizam automaticamente em tempo real via sinal `imagem_alterada`.
- **Diálogo de Adição de Mapas Robusto (`DialogoAdicionarMapa`)**:
  - Interface moderna com botão explícito "Selecionar Imagem..." e suporte a Drag & Drop.
  - Painel de metadados ricos exibindo resolução ($W \times H$), tamanho formatado (KB/MB) e formato de origem detectado.
  - Campo de nome de arquivo inteligente com sanitização automática de slug em tempo real (`sanitizar_nome_imagem`), preview do caminho de destino (`imagens/slug.webp`) e alerta visual imediato em caso de colisão de nomes na RAM ou no disco.
  - Pré-processamento e compressão WebP automática em memória via biblioteca pura `processar_e_comprimir_imagem_para_webp`.
- **Substituição de Imagem no Editor de Mapas (`WidgetEditorMapas`)**:
  - Botão e ação "Substituir Imagem..." na barra de ferramentas do mapa, permitindo trocar o arquivo de fundo em RAM preservando os Pontos de Interesse (POIs) e geometrias existentes, com pré-processamento WebP e suporte a Undo/Redo.
- **Atalho do Mapa para o Editor de Imagens (`WidgetEditorMapas`)**:
  - Ação "Abrir no Editor de Imagens" no Editor de Mapas que comuta a visualização para a aba de imagens da Janela Principal, selecionando automaticamente a imagem correspondente.
- **Substituição de Imagem no Editor de Imagens (`WidgetEditorImagens`)**:
  - Botão e ação "Substituir Imagem..." na lista de imagens, permitindo escolher um novo arquivo, aplicando o pré-processamento WebP em RAM e atualizando a visualização e lista com suporte a Undo/Redo no histórico global.

## Capabilities

### Modified Capabilities
- `editor-mapas`: O sistema SHALL permitir a substituição da imagem de fundo de mapas existentes estritamente em memória RAM com suporte a `QUndoCommand` e pré-processamento WebP, fornecer atalho para focar a imagem no Editor de Imagens, sincronizar reativamente quando a imagem for alterada externamente, e apresentar diálogo enriquecido com metadados e validação de nomes ao adicionar novos mapas.
- `editor-imagens`: O sistema SHALL permitir a substituição do conteúdo de imagens existentes estritamente em memória RAM com pré-processamento WebP, sincronização reativa global entre todas as visões e suporte integral a histórico de alterações (`QUndoCommand`).

## Impact

- **Módulos Afetados**:
  - `editor/models/croqui_model.py`: Inclusão do sinal `imagem_alterada` e suporte reativo a leitura/escrita em memória RAM.
  - `editor/controllers/croqui_controller.py`: Comandos `QUndoCommand` dedicados para substituição de imagens e adição/remoção de mapas em RAM.
  - `editor/views/dialogos/dialogo_adicionar_mapa.py`: Reestruturação completa do diálogo com metadados, validações reativas e compressão WebP em RAM.
  - `editor/views/widget_editor_mapas.py`: Inclusão das ações de substituição de imagem (via comando) e foco no editor de imagens, além de assinatura do sinal `imagem_alterada`.
  - `editor/legacy_views/widget_editor_imagens.py`: Inclusão do botão de substituição de imagens (via comando) e assinatura do sinal `imagem_alterada`.
  - `editor/legacy_views/area_principal.py`: Conexão de sinais de foco e navegação entre mapas e imagens.
  - `editor/core/processamento_imagem_campo.py`: Utilização consistente da biblioteca pura de compressão e metadados.
- **Testes**:
  - Testes unitários novos e atualizados com 100% de cobertura nos diálogos, comandos de Undo/Redo, editores e componentes de visualização.
