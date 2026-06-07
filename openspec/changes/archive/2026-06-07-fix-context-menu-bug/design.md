## Context

No `WidgetEditorDados`, os menus de contexto interagem com itens da árvore que representam mensagens do Protobuf. Quando um menu é aberto com o botão direito, capturamos o `QModelIndex` clicado. Entretanto, devido à mecânica do framework Qt, instâncias nativas do `QModelIndex` expiram facilmente assim que qualquer layout ou re-pintura acontece. Isso é extremamente notável para nós recém-adicionados. Quando a função contendo o lambda tenta utilizar o `QModelIndex` guardado para acionar uma mutação (ex: exclusão), o ponteiro retorna vazio, falhando a macro sem erros (silent failure).

Adicionalmente, existe um pequeno vazamento lógico em `_localizar_no_por_indice`, onde a recursividade busca pelo primeiro "nome do nó expando" que encontrar a partir do topo da árvore, podendo retornar um nó com o mesmo nome em outro galho caso haja multiplas coleções de `Picos` com `Setores`.

## Goals / Non-Goals

**Goals:**
- Garantir que a ação no menu de contexto de qualquer elemento repetido seja despachada com sucesso, não sendo influenciada pela volatibilidade do `QModelIndex`.
- Assegurar que ao adicionar um novo registro que gera expansão, o nó recém-adicionado e selecionado seja aquele exatamente correspondente à coleção em foco, não do primeiro registro irmão do nó raiz.

**Non-Goals:**
- Alterar as assinaturas do controller ou macro; o reparo é restrito à forma que a View interage e gerencia ponteiros do modelo do Qt.

## Decisions

1. **Uso do QPersistentModelIndex:** Todos os `lambdas` conectados aos botões de ação do Menu de Contexto que requerem passar o `QModelIndex` serão encapsulados num `QPersistentModelIndex`.
   *Porquê:* Essa classe provida pelo framework Qt foi designada com esse exato objetivo, resolvendo a invalidação por re-layouts que ocorrem quando a *event queue* é engarrafada por `menu.exec()`.

2. **Scoping do _localizar_novo_idx:** Modificar `_localizar_novo_idx` para inicializar sua busca em `parent_idx` baseada no `QModelIndex` do `expando_node` diretamente ou de seu pai imediato, e não chamando `index(0,0)` para forçar recursividade global.

## Risks / Trade-offs

- **[Risco] Incompatibilidade sintática com _executar_*:** Pode haver uma leve incompatibilidade caso o `QPersistentModelIndex` não contenha exatos os mesmos getters do tipo não persistente em partes específicas.
  *Mitigação:* Fazer downcast do `QPersistentModelIndex` para `QModelIndex` comum dentro da declaração do lambda ao entregá-lo para a call: `lambda checked=False, p=p_index: self._executar_remover_item(QModelIndex(p))`
