# Design

## Context

Atualmente, o [`PainelReferencias`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/widget_painel_referencias.py) renderiza cada referência em um [`CardReferencia`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/widget_painel_referencias.py#L15), conectando os eventos `hover_in` e `hover_out` aos métodos `destacar_pois_temporariamente` e `remover_destaque_pois` de [`WidgetEditorMapas`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/widget_editor_mapas.py).

Quando o usuário clica sobre o card, o evento não é capturado e nenhum estado de seleção é retido. Ao retirar o cursor de cima do painel lateral, o método `remover_destaque_pois()` desarma o highlight ciano de todos os POIs porque não existe um ponteiro para uma referência selecionada persistente.

## Goals / Non-Goals

**Goals:**
- Prover seleção persistente de referências no painel lateral ao clicar no card, mantendo o highlight em ciano dos POIs correspondentes no mapa mesmo após o mouse deixar o painel.
- Suportar pré-visualização temporária via hover sobre outros cards sem perder o highlight da referência selecionada após a saída do mouse.
- Suportar desmarcação (toggle) ao clicar novamente no card selecionado ou clicar em área vazia do mapa.
- Permitir seleção bidirecional: clicar em um POI no mapa em modo de navegação normal localiza sua referência, seleciona o card no painel direito e rola a lista para deixá-lo visível.
- Manter 100% de cobertura de testes unitários sem regressões nos modos de linkagem, câmera e histórico Undo/Redo.

**Non-Goals:**
- Não alterar a estrutura do Protobuf (`croqui.proto`) nem mensagens de dados.
- Não alterar a mecânica dos modos modais de edição (`modo_linkagem`, `modo_camera`, `modo_nova_rota`).

## Decisions

### 1. Interceptação de clique no `CardReferencia` via `mousePressEvent`
- **Decisão**: Implementar `mousePressEvent` em `CardReferencia` que emite sinal de clique. Cliques que atinjam botões filhos (`btn_linkar`, `btn_camera`, `btn_editar_alvo`, `btn_remover`, `btn_inverter`) são tratados pelos próprios botões e não disparam a seleção do card.
- **Alternativas consideradas**:
  - *Adicionar um botão explícito "Selecionar" no card*: Rejeitada por sobrecarregar a interface visual e ser contra intuitiva em comparação a clicar no próprio card.
  - *Usar QListWidget*: Rejeitada porque `CardReferencia` já possui layout rico, botões contextuais e preview de codenomes.

### 2. Estilização dinâmica do estado selecionado
- **Decisão**: Criar método `definir_selecionado(selecionado: bool)` em `CardReferencia` que atualiza seu visual com borda destacada (`2px solid #007bff`), fundo sutil (`#f0f7ff`) e define o cursor para `PointingHandCursor`.
- **Alternativas consideradas**:
  - *Mudar apenas a cor do texto*: Rejeitada por ter baixo contraste e feedback visual fraco.

### 3. Cascata de Fallback em `remover_destaque_pois`
- **Decisão**: Estender `remover_destaque_pois` em `WidgetEditorMapas` para considerar `referencia_selecionada`:
  ```python
  if not force:
      if getattr(self, "referencia_camera_ativa", None):
          self.destacar_pois_temporariamente(self.referencia_camera_ativa)
      elif getattr(self, "referencia_linkagem_ativa", None):
          self.destacar_pois_temporariamente(self.referencia_linkagem_ativa)
      elif getattr(self, "referencia_selecionada", None):
          self.destacar_pois_temporariamente(self.referencia_selecionada)
  ```
- **Rationale**: Permite que o hover continue funcionando como um preview instantâneo: ao passar o mouse em outro card B, o mapa mostra B; ao sair, o mapa restaura automaticamente a referência A selecionada.

### 4. Preservação de Seleção na Reconstrução de Cards
- **Decisão**: Em `PainelReferencias.atualizar_cards()`, salvar o índice selecionado previamente antes de limpar o layout e restaurar o estado selecionado se o índice permanecer válido no mapa recarregado.

### 5. Seleção Bidirecional pelo Mapa
- **Decisão**: Em `WidgetEditorMapas`, quando um POI receber clique em modo normal (fora do modo de linkagem), verificar em `self.msg_mapa_proxy.referencias` qual referência contém o `id` daquele POI. Se encontrada, acionar `painel_referencias.selecionar_referencia(idx)` e centralizar o card no painel via `scroll_area.ensureWidgetVisible(card)`.

## Risks / Trade-offs

- **[Risk] Conflito com movimentação de POIs no mapa** → O clique simples no POI para seleção não impede que o usuário o arraste se mantiver o botão pressionado e mover o mouse; a seleção da referência ocorre imediatamente no clique.
- **[Risk] Atualizações reativas desincronizarem a referência selecionada** → Salvar o índice selecionado em `atualizar_cards` e validar limites de tamanho de array evita índices inválidos ou exceções `IndexError`.
