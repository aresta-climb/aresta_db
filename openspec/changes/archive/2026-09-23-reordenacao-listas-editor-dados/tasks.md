## 1. Controles Visuais e Suporte em Componentes

- [x] 1.1 Criar a alça de arraste `AlcaArrasteItem` com estilo visual discreto (`⠿`), cursor apropriado (`OpenHandCursor`) e sinalização de início de arraste.
- [x] 1.2 Atualizar `WidgetColapsavel` adicionando o método `definir_prefixo_titulo(novo_prefixo)` para permitir atualizar o índice no título preservando o estado do accordion e o título heurístico.

## 2. Botões de Ação Rápida e Sincronização do Histórico

- [x] 2.1 Adicionar os botões de ação rápida "Subir" (▲) e "Descer" (▼) em cada linha de item (primitivos e mensagens) no `ContainerRepeatedWidget`.
- [x] 2.2 Conectar os cliques de "Subir" e "Descer" aos métodos `controller.mover_repeated_para_cima` e `controller.mover_repeated_para_baixo`, garantindo consolidação de edições pendentes.
- [x] 2.3 Conectar o sinal do modelo `model.repeated_movido` ao método `_on_item_movido` no `__init__` do `ContainerRepeatedWidget`.
- [x] 2.4 Implementar `_atualizar_indices_e_botoes()` para reindexar `repeated_index`, `protobuf_field`, cabeçalhos colapsáveis e habilitar/desabilitar botões nos extremos da lista.

## 3. Mecanismo de Drag and Drop no Layout da Lista

- [x] 3.1 Implementar a criação do `QDrag` com MIME type `application/x-aresta-repeated-item` contendo ID da mensagem pai, nome do campo e índice de origem.
- [x] 3.2 Habilitar `setAcceptDrops(True)` e implementar `dragEnterEvent`, `dragMoveEvent`, `dragLeaveEvent` e `dropEvent` no `ContainerRepeatedWidget`.
- [x] 3.3 Implementar indicador visual de linha de inserção (drop indicator) entre os itens durante o arraste.
- [x] 3.4 Processar o drop no `dropEvent`, calculando o índice de destino com base na coordenada Y do mouse e despachando `controller.mover_repeated_para_posicao`.

## 4. Testes e Verificação

- [x] 4.1 Criar testes em `editor/views/widget_editor_dados_test.py` cobrindo o acionamento dos botões ▲ e ▼ (primeiro item, último item, item intermediário e lista de tamanho 1).
- [x] 4.2 Criar testes simulando eventos de drag-and-drop no `ContainerRepeatedWidget`, validando a nova ordenação e rejeição de itens inválidos ou externos.
- [x] 4.3 Criar testes validando a reversibilidade completa de reordenações via `Undo` (`Ctrl+Z`) e `Redo` (`Ctrl+Y`).
- [x] 4.4 Executar suíte de testes do editor (`pytest editor/ -m "not slow"`) para garantir 100% de aprovação e ausência de regressões.
