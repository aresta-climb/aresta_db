# Design

## Context

Conforme descrito em `proposal.md`, a importação de croquis oficiais e a criação de croquis novos no Editor Aresta ainda carregam o conceito legado de `resumo_edicao`, que exibia um `QInputDialog` bloqueante ao importar croqui oficial, gravava `"Inicialização automática"` em croquis novos e renderizava uma linha extra em itálico no `WidgetItemHistorico`. Além disso, o `DialogoBuscaCroqui` usa `QListWidget.setRowHidden` para filtrar itens sem atualizar a linha selecionada (`currentRow`), obrigando o usuário a clicar no primeiro item filtrado antes de pressionar `Enter` (ou correndo o risco de confirmar um item oculto caso houvesse seleção prévia).

## Goals / Non-Goals

**Goals:**
- Garantir fluxo 100% operável por teclado no `DialogoBuscaCroqui`: abrir diálogo -> digitar filtro -> pressionar `Enter` -> importar imediatamente.
- Remover `CroquiExperimental.resumo_edicao` do schema Protobuf com `reserved 4;` e eliminar todo o código morto associado no `editor/`, `aresta_api/` e ferramentas MCP, blindando a remoção no teste de contrato AST.
- Refatorar os testes de `dialogo_busca_croqui_test.py` e `tela_de_carregamento_test.py` tocados pela mudança para eliminar `MagicMock` e `patch` de componentes internos (Princípios V e VII do `AGENTS.md`).

**Non-Goals:**
- Alterar o fluxo de publicação de Pull Requests (`PublishDialog`), que já possui seu próprio título e descrição independentes de `resumo_edicao`.

## Decisions

### 1. Seleção automática do primeiro item visível em `DialogoBuscaCroqui`
- **Escolha**: Introduzir um método auxiliar `_selecionar_primeiro_visivel()` chamado ao final de `carregar_indice()` e de `filtrar_lista(texto)`. Ele percorre os índices de `0` até `count() - 1` buscando o primeiro índice `i` onde `not self.lista_croquis.isRowHidden(i)`. Se encontrar, chama `self.lista_croquis.setCurrentRow(i)`; caso contrário, chama `self.lista_croquis.setCurrentRow(-1)` e `self.lista_croquis.clearSelection()`. Adicionalmente, `obter_id_selecionado()` verificará se `currentRow() >= 0` e `not isRowHidden(currentRow())` antes de extrair o ID.
- **Racional**: `QListWidget.setRowHidden(i, True)` oculta visualmente a linha, mas o Qt não desmarca `currentRow()` automaticamente se aquela linha já estava selecionada. Atualizar explicitamente para a primeira linha visível (ou `-1` quando vazio) garante que o botão `Confirmar` (`setDefault(True)`) reflita exatamente se há um item visível selecionado e que `Enter` no `campo_busca` sempre confirme o item do topo da lista filtrada.
- **Alternativas consideradas**: Recriar todos os `QListWidgetItem` a cada tecla digitada (como em `WidgetBuscaEntidades`). Descartado porque `setRowHidden` sobre a lista já carregada em memória é mais simples, preserva as instâncias já criadas e requer apenas sincronizar `currentRow`.

### 2. Remoção de `resumo_edicao` no Protobuf (`reserved 4;`) e proteção via AST
- **Escolha**:
  1. Remover `string resumo_edicao = 4;` de `aresta_api/proto/croqui_experimental.proto`, adicionar `reserved 4;` ao final de `CroquiExperimental` e regerar os módulos em `aresta_api/proto/generated/`.
  2. Estender `tests/contrato_campos_deprecados_protobuf_test.py` para detectar qualquer acesso ou passagem de argumento `resumo_edicao` na AST de `editor/`, `scripts/` e `serving/`.
  3. Remover o parâmetro `resumo_edicao` de `GerenciadorCroquiExperimental._criar_estrutura_croqui`, `criar_novo_croqui`, `criar_croqui_a_partir_de_oficial` e da ferramenta MCP `aresta_importar_croqui_oficial`, bem como `label_resumo` de `WidgetItemHistorico` e o `QInputDialog.getText` de `TelaDeCarregamento.ao_clicar_oficial`.
- **Racional**: Reserva a tag `4` no `.proto` para impedir reutilização acidental, enquanto `ParseDict(..., ignore_unknown_fields=True)` em `GerenciadorCroquiExperimental.abrir_croqui` garante compatibilidade com YAMLs antigos e o teste de contrato AST impede regressões.

## Risks / Trade-offs

- **[Risk] Arquivos `croqui_experimental.yaml` antigos no disco do usuário contendo a chave `resumo_edicao`** → **Mitigação**: `ParseDict(dados, meta, ignore_unknown_fields=True)` em `GerenciadorCroquiExperimental.abrir_croqui` ignora chaves desconhecidas e regrava o YAML limpo na abertura seguinte.
- **[Risk] Chamadas de agentes de IA usando o argumento antigo `resumo_edicao` em `aresta_importar_croqui_oficial`** → **Mitigação**: O manipulador `_importar_croqui_oficial` ignora chaves extras no dicionário `args` (`args.get("id_oficial")`), e atualizaremos `.agents/skills/separar_croqui_pdf_em_partes/SKILL.md` e `.agents/workflows/atualizar_croqui_completo.md` para não mencionarem mais o parâmetro.
