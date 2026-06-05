## Context

O editor de dados reconstrói toda a árvore de navegação e o formulário atual sempre que o histórico (`QUndoStack`) sofre uma mutação (undo/redo). O recarregamento e o redesenho constante causam uma experiência de uso frustrante: a UI sofre "flickers", o teclado perde o foco e o scroll é resetado. A abordagem proposta adota o padrão Observer reativo através do mecanismo nativo de Signals/Slots do Qt.

## Goals / Non-Goals

**Goals:**
- Eliminar o recarregamento total (`load_node`) automático causado puramente por eventos de Undo/Redo no editor de dados.
- Restaurar o foco (`setFocus()`) e a seleção (`selectAll()`) automaticamente ao widget de campo afetado após um comando ser revertido ou refeito.
- Suportar a inserção e remoção suaves e modulares (sem redesenhar o nó inteiro) para campos do tipo *Repeated* via manipulação direta de layouts (usando `insertWidget`).

**Non-Goals:**
- Substituir a lógica flexível de *reflection* (descritores) atual por `QDataWidgetMapper` nativo (overhead de engenharia excessivo).
- Substituir o design existente do `QUndoCommand` por outra biblioteca de state management.

## Decisions

**1. Sinais Estruturados via Barramento de Eventos**
O sistema precisará emitir sinais quando um comando for executado/desfeito/refeito. Vamos criar ou reutilizar um objeto global observável (como o `GerenciadorHistorico` ou `AtualizadorUI`) com os seguintes sinais PyQt6/PySide6:
- `sinal_campo_alterado(int id_msg, str campo, Any novo_valor)`
- `sinal_item_adicionado(int id_msg, str campo, int indice)`
- `sinal_item_removido(int id_msg, str campo, int indice)`

**Rationale:** O padrão Observer desacopla completamente o disparo do histórico e a atualização da UI.

**2. Widgets Reativos Primitivos**
Ao renderizar um campo primitivo em `ProtobufWidgetFactory`, conectaremos dinamicamente o `sinal_campo_alterado` a um slot específico daquele widget gerado. O slot validará:
```python
if id_msg == id(msg) and campo == field.name:
    widget.blockSignals(True)
    # atualizar visualmente (ex: setText)
    widget.blockSignals(False)
    widget.setFocus()
```
**Rationale:** Como a UI cria e destrói esses widgets on-demand ao trocar de nó selecionado na árvore, gerenciar a reatividade no próprio componente elimina os antigos dicionários ou atualizações maciças.

**3. ContainerRepeatedWidget para Estruturas Dinâmicas**
Vamos extrair a lógica inline de `_render_repeated_field` presente no `WidgetFormularioPadrao` para um componente modular `ContainerRepeatedWidget`.
Esse container assinará aos sinais `sinal_item_adicionado` e `sinal_item_removido`.
- Quando um item é adicionado (Redo), ele renderizará apenas a subseção correspondente e usará `layout.insertWidget(indice, novo_conteudo)`.
- Quando removido (Undo), ele usará `itemAt(indice)` para encontrar a subseção visual e chamar `deleteLater()`.

**Rationale:** Solução muito similar à forma como Item Models nativos lidam com `beginInsertRows`.

**4. Reatividade da Árvore de Navegação (ProtobufTreeModel)**
A árvore à esquerda (`ProtobufTreeModel`) também será uma Observadora dos mesmos sinais estruturais e primitivos.
- `sinal_campo_alterado`: Se o campo modificado for o *label* (ex: nome do Pico), a árvore emite `dataChanged(index, index)` para atualizar só o texto exibido.
- `sinal_item_adicionado` e `sinal_item_removido`: O modelo da árvore invocará as APIs nativas `beginInsertRows` e `beginRemoveRows` atualizando sua estrutura interna hierárquica sob demanda.

**Rationale:** Garante consistência global entre os nós de hierarquia e as edições de formulário, além de preservar inteiramente a expansão das pastas da árvore durante Desfazer/Refazer.

## Risks / Trade-offs

- **[Risk] Vazamento de Memória com Conexões (Memory Leaks):** No PySide6/PyQt6, se conectarmos closures locais (`lambda` ou `def` aninhada) a sinais globais do `GerenciadorHistorico` que sobrevive por toda a aplicação, os widgets podem não ser coletados pelo Garbage Collector quando o formulário for trocado.
  **Mitigation:** Todas as conexões devem explicitamente verificar o ciclo de vida usando `functools.partial` sem closures fortes, ou desconectando manualmente durante os ciclos de destruição. Alternativamente, os sinais globais avisam o `WidgetFormularioPadrao`, que faz o roteamento dos sinais apenas para as conexões filhas ativas e as destrói no momento de recarregar a tela.
- **[Risk] Mutações de ID Inesperadas:** Usar `id(msg)` assume que a instância do objeto Protobuf em memória não muda, mas apenas os seus conteúdos são mutados in-place pelos comandos.
  **Mitigation:** O design de comandos foi construído propositalmente para mutações in-place, tornando seguro o uso dos endereços de memória para identificar a mesma instância. O teste contínuo focará na validação disso.
