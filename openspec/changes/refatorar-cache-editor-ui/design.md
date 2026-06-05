## Context

Atualmente o editor de dados (construído no `WidgetEditorDados`) destrói toda a hierarquia visual (`QWidget` interno) a cada mudança de seleção na árvore ou, incrivelmente, a cada dígito inserido caso essa inserção dispare eventos estruturais incorretos no modelo (`layoutChanged`, `rebuild_tree`). Isso causa a perda de scroll, foco, e torna a UI lenta e instável ("pulando"). O ProtobufTreeModel também possui métodos pesados (`rebuild_tree`) que quebram o cache de indexação.

## Goals / Non-Goals

**Goals:**
- Manter instâncias vivas de cada formulário usando um `QStackedWidget`.
- Eliminar o uso do recarregamento bruto (`layoutChanged` e `rebuild_tree`) para mutações finas (ex: inserir ou editar um item).
- Alinhar nomes à arquitetura limpa: `ProtobufTreeModel` deve focar em View e ser um "Adapter".

**Non-Goals:**
- Não iremos introduzir funcionalidades de negócio novas ao editor (novos botões complexos, abas não planejadas).
- Não faremos migração para outra biblioteca de interface (o Qt será mantido).

## Decisions

1. **Cache através de `QStackedWidget`**: 
   - *Por que:* O Stack permite guardar múltiplas instâncias complexas (como um form inteiro) na memória da janela.
   - *Alternativas:* Usar Dicts e setWidget() em um QScrollArea estático. O QStackedWidget é nativo, otimizado para isso, e suporta empilhamento real sem bugs de repintura do QScrollArea se cada form for o próprio QScrollArea.
2. **Reatividade Fina**:
   - *Por que:* O QAbstractItemModel do Qt já lida bem com `beginInsertRows`/`dataChanged`. O modelo (`ProtobufTreeModel`) será responsável por emitir exatamente as áreas impactadas, permitindo à UI se animar sem perder posições na tela.
3. **Renomeação para Adapter**:
   - *Por que:* `ProtobufTreeModel` hoje reside em `core`, e carrega o sufixo "model". Sendo puramente uma classe de View/Adapter para Qt, ele deve ir para `views` sob o nome `ProtobufTreeViewAdapter`.

## Risks / Trade-offs

- **[Risk] Aumento do uso de Memória** → Como manteremos os formulários cacheados, a memória consumida será ligeiramente maior para croquis gigantes. *Mitigação:* O GC do Python e o overhead do Qt para widgets invisíveis é muito pequeno hoje em dia. Vale 100% o trade-off pela UX superior.
- **[Risk] Dessincronização do form em background** → *Mitigação:* O form já tem uma excelente ponte via `_on_campo_alterado` e eventos de undo. Os forms inativos continuam recebendo sinais.
