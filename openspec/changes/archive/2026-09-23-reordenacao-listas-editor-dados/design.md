# Design Técnico: Reordenação de Listas no Editor de Dados

## Context

No editor de dados, coleções repetidas de mensagens e tipos primitivos (como escaladas, vias, sinônimos, variantes e pontos de interesse) são gerenciadas pelo componente `ContainerRepeatedWidget` e empilhadas em um layout vertical (`QVBoxLayout`).

O backend e o histórico já possuem suporte completo a movimentações atômicas com reversibilidade via `CmdMoverRepeated`, `croqui_controller.mover_repeated_para_posicao`, `croqui_controller.mover_repeated_para_cima`, `croqui_controller.mover_repeated_para_baixo` e o sinal `croqui_model.repeated_movido`. No entanto, na camada de visão (`ContainerRepeatedWidget`), não existem botões de movimentação nem suporte a drag-and-drop, e o sinal `repeated_movido` não foi conectado.

## Goals / Non-Goals

**Goals:**
- Prover botões de ação rápida "Subir" (▲) e "Descer" (▼) em cada item de lista com atualização dinâmica de estado habilitado/desabilitado nos limites da coleção.
- Prover alça visual de arraste (`⠿`) em cada item para reordenação contínua por arrastar e soltar (drag-and-drop).
- Exibir indicador visual de linha de inserção durante o arraste sobre o container da lista.
- Conectar o sinal `model.repeated_movido` e atualizar títulos indexados de itens colapsáveis (`WidgetColapsavel`) e propriedades internas.
- Garantir histórico atômico com suporte a `Ctrl+Z` (Undo) e `Ctrl+Y` (Redo).

**Non-Goals:**
- Mover itens entre listas ou mensagens diferentes (ex: transferir uma escalada de um setor para outro não faz parte deste escopo).
- Alterar o comportamento de drag-and-drop da árvore de dados lateral (`ArvoreDadosTreeView`), que já foi implementado e arquivado.

## Decisions

### Decisão 1: Alça de Arraste (`⠿`) dedicada
- **Decisão**: Cada linha de item terá um botão/rótulo dedicado atuando como alça de arraste (`⠿`). O evento de `QDrag` só é disparado quando o arraste é iniciado a partir dessa alça (com `QApplication.startDragDistance()`).
- **Justificativa**: Evita conflitos com a seleção de texto de `QLineEdit`, interação com `QComboBox`/`QSpinBox` e cliques para expandir/colapsar o accordion em `WidgetColapsavel`.
- **Alternativas consideradas**: Permitir arrastar a linha inteira (descartado por conflitar com foco de campos e cliques normais).

### Decisão 2: Manter `QVBoxLayout` com linha indicadora de soltura em vez de `QListWidget`
- **Decisão**: O `ContainerRepeatedWidget` continuará usando `QVBoxLayout`, implementando `dragEnterEvent`, `dragMoveEvent`, `dragLeaveEvent` e `dropEvent`. Um widget indicador fino (linha horizontal azul) será movido dinamicamente entre os itens para indicar onde a soltura ocorrerá.
- **Justificativa**: `WidgetColapsavel` tem altura altamente variável e dinâmica (expande e recolhe). Usar `QListWidget` com `setItemWidget` gera bugs crônicos no Qt de cálculo de tamanho, eventos de teclado e rolagem. O layout vertical nativo já é estável e responsivo.
- **Alternativas consideradas**: `QListWidget` (descartado pelos problemas com `setItemWidget` e foco no Windows).

### Decisão 3: MIME Data tipado com validação de escopo
- **Decisão**: O MIME transportado no `QDrag` será `application/x-aresta-repeated-item`, contendo uma payload serializada com o identificador da mensagem pai (`_get_id(self.msg)`), o nome do campo (`self.field.name`) e o índice de origem (`index_origem`).
- **Justificativa**: Garante que o container rejeite qualquer drop que venha de outra lista ou de fora do formulário.

### Decisão 4: Sincronização e Reindexação Dinâmica em `_on_item_movido`
- **Decisão**: Ao receber o sinal `repeated_movido`, o container reordena o widget no layout e invoca um método de atualização (`_atualizar_indices_e_botoes()`) que:
  1. Atualiza `repeated_index` em cada widget filho.
  2. Atualiza `protobuf_field` em campos primitivos.
  3. Atualiza o prefixo do título em `WidgetColapsavel` através de um novo método `definir_prefixo_titulo(novo_prefixo)`, mantendo o estado de expansão e título heurístico.
  4. Habilita/desabilita os botões "Subir" e "Descer" (`btn_subir.setEnabled(i > 0)`, `btn_descer.setEnabled(i < total - 1)`).

## Risks / Trade-offs

- **[Risco]** Itens colapsáveis muito altos podem dificultar a visualização da linha de inserção.  
  → *Mitigação*: A linha indicadora terá espessura de 3px com cor de destaque (#2b579a), e o pixmap fantasma do cursor exibirá uma versão compacta do cabeçalho do item.
- **[Risco]** Edições pendentes em temporizador de coalescência ao clicar em subir/descer ou soltar.  
  → *Mitigação*: Antes de invocar o método do controlador, chama descarregamento preventivo e marcação de dirty.
