## ADDED Requirements

### Requirement: Renderização Direta de Card Visual para Mapas em Coleções Repetidas
O sistema SHALL renderizar itens de coleções repetidas do tipo `Mapa` (ou com anotação `mensagem_formato_na_ui = MAPA`) diretamente como cartões visuais abertos, sem encapsulamento em accordion colapsável (`WidgetColapsavel`).
- **Barra de Controle Superior**: Cada cartão SHALL exibir no topo uma alça de arraste `⠿`, o título composto pelo índice e nome do arquivo da foto (ex: `Mapa [0] - setor_fugitivos_p0.webp`), os botões de ação rápida `▲` (Subir) e `▼` (Descer), e o botão `Remover`.
- **Corpo Visual**: Cada cartão SHALL exibir uma miniatura com proporção preservada da imagem (`caminho_imagem_mapa`), as dimensões em pixels (`largura_mapa × altura_mapa`), o caminho relativo do arquivo e o botão de ação `Abrir no Editor de Mapas`.
- **Tratamento de Imagem Ausente**: Caso o arquivo da imagem não exista ou não possa ser lido, o cartão SHALL exibir um indicador visual de imagem ausente/placeholder sem interromper o fluxo da interface.

#### Scenario: Visualização de cartão de mapa no formulário
- **WHEN** o formulário de uma mensagem contendo mapas (ex: setor ou pico) é exibido
- **THEN** cada item da coleção de mapas SHALL ser renderizado como um cartão aberto com sua foto em miniatura, metadados de resolução e botão para o editor de mapas, sem botão de colapso/expansão.

#### Scenario: Visualização de mapa sem arquivo de imagem
- **WHEN** um mapa cadastrado não possui arquivo de imagem disponível no disco ou na memória
- **THEN** o cartão correspondente SHALL exibir um marcador de "Sem Imagem" no espaço da miniatura e desabilitar ações que dependam da imagem física.

### Requirement: Atualização e Sincronização de Cards de Mapa na Reordenação
O sistema SHALL sincronizar os cartões visuais de mapas ao responder ao sinal de movimentação no modelo (`repeated_movido`).
- Os índices nos títulos dos cartões (`Mapa [i]`) SHALL ser atualizados para refletir a nova posição contígua.
- Os botões `▲` e `▼` SHALL ter seus estados recalculados (desabilitando `▲` no índice 0 e `▼` no último índice).
- O reposicionamento do cartão no layout SHALL preservar a miniatura carregada e os metadados do mapa.
- A operação de movimentação SHALL ser despachada via comando no histórico (`CmdMoverRepeated`), garantindo reversibilidade com Desfazer (Undo) e Refazer (Redo).

#### Scenario: Reordenação de cards de mapa por botões ou arraste
- **WHEN** o usuário move um cartão de mapa para outra posição via botão ou drag-and-drop
- **THEN** o cartão do mapa com sua respectiva miniatura e dados SHALL se mover para a nova posição no layout
- **AND** os índices e botões de limite de todos os cartões da coleção SHALL ser atualizados.

#### Scenario: Desfazer reordenação de card de mapa
- **WHEN** o usuário desfaz (Undo) uma movimentação de mapa
- **THEN** o cartão do mapa e sua miniatura SHALL retornar à posição anterior na listagem visual e no Protobuf.
