# Design Técnico: Sincronização de Mensagens e Prevenção de Nós Órfãos

## Context

No ecossistema do editor Aresta, o `CroquiModel` gerencia mutações da árvore Protobuf e despacha sinais Qt (`repeated_movido`, `dado_alterado`, etc.).
O `ProtobufTreeViewAdapter` espelha a hierarquia de mensagens como `ProtobufNode`s, e o `FormularioPadrao` renderiza formulários baseados em cards para a mensagem selecionada, guardando instâncias em `cached_forms`.

No Google Protobuf em Python (`upb`), coleções repeated de mensagens compostas (`RepeatedCompositeContainer`) não suportam atribuição direta (`lista[i] = val`). Quando `CroquiModel._mover_repeated` executa `pop(index_from)` e `insert(index_to, item)`, o Protobuf cria uma nova instância de mensagem em memória no índice de destino e copia os campos de `item`. O objeto original desanexado torna-se órfão.

Como a árvore e o formulário mantinham ponteiros para o objeto antigo, qualquer mutação posterior através de `CmdAlterarPrimitivo` falha na validação `validar_pertence_ao_croqui`.

## Goals / Non-Goals

**Goals:**
- Garantir que `ProtobufNode.message` e toda a sub-árvore de nós populados afetados por um movimento repeated apontem para as novas instâncias vivas no Protobuf.
- Garantir que qualquer digitação pendente no formulário (agendada via `TemporizadorCoalescencia`) seja descarregada no Protobuf antes de executar o movimento.
- Garantir que `FormularioPadrao` descarte caches obsoletos de mensagens movidas e recarregue os widgets vinculados à instância viva.
- Manter a estabilidade do `QTreeView`, preservando linhas expandidas, foco e seleção sem colapsar a árvore.

**Non-Goals:**
- Modificar as classes internas do Protobuf ou substituir `_mover_repeated` por cópias manuais de atributos em cascata.
- Usar `beginResetModel` no modelo de árvore, pois isso reiniciaria o estado visual e colapsaria todos os nós abertos.

## Decisions

### 1. Sincronização Recursiva de Referências em `ProtobufTreeViewAdapter._on_item_movido`
**Decisão**: Em `_on_item_movido`, após reordenar a lista `exp_node.children`, iterar no intervalo afetado (`min_idx` a `max_idx`) e atualizar a mensagem de cada nó filho `c` com `exp_node._resolve_transparency(repeated_container[i])`. Se `c` já tiver sido populado (`c._is_populated == True`), invocar uma sincronização recursiva:
- Para cada nó filho de `c` que seja um expando (`is_expando == True`), se estiver populado, atualizar os itens de sua coleção correspondente no novo pai.
- Para cada nó filho que seja submensagem singular, atualizar `sub_node.message` com a submensagem correspondente da nova mensagem.

**Alternativas consideradas**:
- *Recriar os filhos do expando (`exp_node.children.clear()` e `_populate_children()`)*: Rejeitado porque colapsa a hierarquia expandida do nó movido e quebra a semântica de `beginMoveRows`/`endMoveRows` do Qt.

### 2. Flush Preventivo de Edições Pendentes em `WidgetEditorDados`
**Decisão**: Criar um método `forcar_consolidacao_pendente()` em `FormularioPadrao` (que percorre o formulário atual, aciona `forcar_consolidacao()` em qualquer `WidgetEditorMarkdown` ou dispara `editingFinished` em campos de texto com foco). Chamá-lo no início de `_executar_mover_para_cima` e `_executar_mover_para_baixo`.

**Alternativas consideradas**:
- *Apenas cancelar o temporizador (`temporizador.descartar()`)*: Rejeitado porque descartaria o texto recém-digitado pelo usuário antes de clicar no botão ou menu de mover.

### 3. Invalidação de Cache de Formulários no `FormularioPadrao`
**Decisão**: Quando um nó com mensagem movida for re-selecionado, remover a chave do ID antigo de `cached_forms` (se presente) e garantir a instanciação de um novo formulário ou a atualização direta da referência da mensagem dos widgets. Como o ID da mensagem mudou para o novo endereço retornado pelo Protobuf, ao expurgar o ID antigo, `load_node` cria um formulário perfeitamente conectado à instância ativa.

**Alternativas consideradas**:
- *Manter o cache e tentar trocar in-place o atributo `self.msg` de todos os widgets filhos*: Frágil devido às múltiplas closures (`make_on_changed`) que capturaram `msg` por valor na criação dos callbacks. Descartar o cache garante reconstrução limpa e segura.

## Risks / Trade-offs

- **[Risco] Reordenação via Undo/Redo**: O usuário pode acionar desfazer/refazer via atalho sem clicar no menu da UI.
  *Mitigação*: A sincronização de referências e atualização de formulário é feita primariamente no slot `_on_repeated_movido`, que é acionado por qualquer origem de mutação no model (inclusive Undo e Redo).

- **[Risco] Sub-árvores profundas (Setor -> Vias -> Lances)**: Nós filhos profundamente aninhados poderiam permanecer com instâncias antigas.
  *Mitigação*: A função de sincronização recursiva desce por todos os nós que possuam `_is_populated == True`, garantindo que todo nó aberto na visualização tenha sua referência atualizada.
