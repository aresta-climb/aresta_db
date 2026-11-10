# Design

## Context

Conforme detalhado em `proposal.md`, o Painel de Qualidade do Croqui (`WidgetPainelQualidade`) emite URIs `ContextoUIPath` ao clicar nos botões de ação das tarefas pendentes. Hoje:
1. `ContextoUIPath` (`editor/core/contexto.py`) reconhece apenas `page:<pagina>`, `file:<arquivo>` e `caminho_local_arvore` (caminho do nó na árvore de dados), sem granularidade de campo.
2. `WidgetEditorDados._on_foco_requisitado` (`editor/views/widget_editor_dados.py`) seleciona o nó na árvore (ou retorna imediatamente se o nó já estiver selecionado), deixando o `QScrollArea` do `WidgetFormularioPadrao` no topo e mantendo `WidgetSecaoAvancada` recolhida mesmo quando a pendência está em um campo avançado.
3. `CardTarefaQualidade.atualizar_tarefa` (`editor/views/widget_painel_qualidade.py`) adiciona o prefixo hardcoded `"Ir para: "` a todos os botões, e `avaliar_nota_qualidade_croqui` (`editor/core/avaliador_nota_qualidade.py`) gera rótulos genéricos por entidade em vez de ações diretas por campo faltante.

## Goals / Non-Goals

**Goals:**
- Estender `ContextoUIPath` com suporte determinístico ao sufixo `/campo:<nome_campo>`.
- Permitir que `WidgetFormularioPadrao` localize qualquer campo renderizado (seja campo primitivo/mensagem em `field_containers`, coleção repetida inline em `ContainerRepeatedWidget`, cartão de subelementos no rodapé em `card_containers` ou seção de betas em `Escalada`), expanda `WidgetSecaoAvancada` quando necessário, faça scroll no `QScrollArea` e dê foco ao widget interativo.
- Revisar os rótulos e URIs das 22 tarefas em `avaliador_nota_qualidade.py` e remover o prefixo `"Ir para: "` em `CardTarefaQualidade`.

**Non-Goals:**
- Alterar os pesos, metas percentuais (`90%` / `50%`) ou regras matemáticas de pontuação da `nota_qualidade`.
- Criar animações assíncronas complexas ou timers bloqueantes na thread de UI.

## Decisions

### 1. Sintaxe `/campo:<nome_campo>` no `ContextoUIPath`
- **Decisão**: Adotar o segmento `/campo:<nome_campo>` ao final do caminho da árvore em URIs da página `dados` (ou sem prefixo de página), expondo `campo_alvo: str | None` em `ContextoUIPath`.
- **Racional**: Segue o Princípio I (`AGENTS.md` - Tudo em Português) e o estilo `chave:valor` já usado nos demais segmentos (`page:`, `node:`, `expando:`, `item:`, `file:`). Ao extrair `/campo:<nome_campo>` no `_parse()`, `caminho_local_arvore` permanece idêntico ao formato esperado por `ProtobufTreeViewAdapter.find_index_for_path`, preservando total compatibilidade com a árvore.
- **Alternativas consideradas**: Query string (`?field=...`) ou sufixo em inglês (`/field:...`), descartadas por fugirem do padrão `chave:valor` em português da base.

### 2. Resolução de Container, Auto-Expansão de Avançados, Scroll e Foco em `WidgetFormularioPadrao`
- **Decisão**:
  1. Guardar na `QScrollArea` do formulário (ou em dicionários indexados por `msg_id` em `WidgetFormularioPadrao`) a referência à `WidgetSecaoAvancada` criada em `_render_message_fields` e aos widgets de campos repetidos (`ContainerRepeatedWidget`) e cartões de rodapé (`card_containers`).
  2. Criar o método público `focar_campo(nome_campo: str) -> bool` em `WidgetFormularioPadrao`:
     - Localiza o widget alvo associado a `(msg_id_atual, nome_campo)` (verificando `field_containers`, `ContainerRepeatedWidget`, `card_containers` e, para `nome_campo == "betas"`, o card `SecaoBetasEscalada`).
     - Se o widget alvo for descendente de uma `WidgetSecaoAvancada` cujo `content_area` não esteja visível (`not secao.toggle_button.isChecked()`), aciona `secao.toggle_button.setChecked(True)` para expandir a seção avançada e atualiza a geometria do layout.
     - No `QScrollArea` ativo, chama `scroll_area.ensureWidgetVisible(widget_alvo, 0, 32)` para rolar até o campo.
     - Localiza o controle interativo prioritário dentro de `widget_alvo` para receber `setFocus()`:
       - Em `WidgetMensagemCoordenada`: se a pendência for gerar malha ou já houver coordenada válida e o botão `btn_gerar_malha` estiver habilitado, ou no input `edit_lat` por padrão.
       - Em `WidgetEditorMarkdown`: no `editor` (`EditorTextoMarkdown`).
       - Em `ContainerRepeatedWidget` ou cartão de subelementos: no último input existente ou no botão `+ Adicionar ...` (`btn_add`).
       - Nos demais cards: no primeiro `QLineEdit`, `QComboBox`, `QSpinBox`, `QDoubleSpinBox`, `QCheckBox` ou `QPushButton` visível e habilitado.
  3. Em `WidgetEditorDados._on_foco_requisitado(path)`:
     - Mesmo quando `curr_path == path_local`, se `ctx.campo_alvo` estiver presente, não retornar prematuramente: chamar `self.form_padrao.focar_campo(ctx.campo_alvo)`.
     - Quando o nó selecionado mudar, após `self._on_tree_selection_changed(None, None)`, se `ctx.campo_alvo` estiver presente, chamar `self.form_padrao.focar_campo(ctx.campo_alvo)`.
     - Na navegação para um item filho (como `.../expando:escaladas/item:0/campo:destaque` na Tarefa 2.5), expandir os índices ancestrais na `tree_view` para que a lista de escaladas fique visível e aberta na árvore lateral.

### 3. Padronização dos Rótulos e URIs nas 22 Tarefas de Qualidade
- **Decisão**:
  - Remover `"Ir para: "` em `CardTarefaQualidade.atualizar_tarefa`, passando a definir `btn.setText(acao.rotulo)`.
  - Nas tarefas de pico (`1.2`, `1.3`, `1.4`, `1.8`, `3.6`), usar um helper `_formatar_rotulo_pico(acao_base: str, nome_pico: str, total_picos: int) -> str` que retorna `acao_base` quando `total_picos == 1` e `f"{acao_base} ({nome_pico})"` quando `total_picos > 1`.
  - Desmembrar tarefas compostas em ações específicas para cada campo pendente (respeitando o limite de exibição dos primeiros botões no card, mas garantindo que um mesmo pico sem localização e sem Google Maps gere imediatamente os 2 botões `"Adicionar localização"` e `"Adicionar link Google Maps"`).

## Risks / Trade-offs

- **[Cálculo de layout antes do scroll após expandir `WidgetSecaoAvancada`]** → Ao expandir `WidgetSecaoAvancada` programaticamente, o layout do `QScrollArea` precisa recalcular a posição vertical do widget recém-exibido antes de `ensureWidgetVisible`. Mitigação: acionar `scroll_area.widget().adjustSize()` / `layout.activate()` imediatamente após `toggle_button.setChecked(True)` (sem usar `processEvents()`).
- **[Mensagens wrapper `ONEOF` / `ONEOF_CONTEUDO`]** → Em `Setor`, `Grupo` e `Escalada`, o nó da árvore aponta para `ArquivoSetor`/`Setor` ou `Escalada` enquanto os campos da modalidade (`dificuldade`, `extensao`, `destaque`, `tipo_parede`, `conquistadores`, `descricao`) pertencem à submensagem ativa do oneof (`via_esportiva`, `via_movel`, `boulder`, etc.). Mitigação: `focar_campo` buscará pelo nome do campo tanto no `msg_id` raiz do nó quanto nas submensagens renderizadas dentro do formulário ativo.
