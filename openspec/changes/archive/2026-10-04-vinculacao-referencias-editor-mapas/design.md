# Design

## Context

No Editor de Mapas (`WidgetEditorMapas`), o painel lateral direito (`PainelReferencias`) exibe os cards de referências lógicas (`CardReferencia`). A associação de elementos gráficos do mapa (círculos e trajetos vetoriais) a uma referência é controlada por um modo interativo ativado pelo botão no card.

Anteriormente, o botão utilizava a inscrição `"Linkar POIs"`, e seu acionamento gerava divergências de estado:
- O card associado ao modo de vinculação não sincronizava sua seleção com o painel (`referencia_selecionada`), permitindo estados cruzados.
- Ao sair do modo ou trocar de referência, o atributo `referencia_linkagem_ativa` retinha a referência anterior, fazendo com que o método `remover_destaque_pois` (disparado pelo `leaveEvent` de hover de outros cards) restaurasse a referência anterior por precedência no fallback.
- O clique em elementos do mapa no modo de vinculação precisa refletir imediatamente o destaque visual em ciano (adicionando ou removendo o elemento).

## Goals / Non-Goals

**Goals:**
- **Internacionalização e Princípio I**: Substituir todos os termos em inglês ("Linkar POIs", "Linkando...", "MODO LINKAGEM") por termos claros em português brasileiro ("Vincular Elementos", "Vinculando...", "MODO VINCULAÇÃO").
- **Acoplamento Sincronizado**: Ao ativar "Vincular Elementos", o card correspondente é selecionado imediatamente no painel (`definir_selecionado(True)`), mantendo a referência ativa e selecionada estritamente alinhadas.
- **Limpeza Atômica de Estado Órfão**: Garantir que `referencia_linkagem_ativa` seja atualizada ou limpa (`None`) ao alternar cards ou desativar o modo, evitando que `remover_destaque_pois` restaure referências anteriores.
- **Feedback Visual Imediato**: Clicar em um elemento não vinculado no mapa o adiciona à referência e destaca-o em ciano imediatamente; clicar em um elemento já vinculado o remove da referência e remove o destaque em ciano imediatamente.
- **Conformidade com os Princípios Aresta**: 100% em português brasileiro, 100% de cobertura de testes unitários (TDD Red-Green-Refactor) e mutações no modelo via comandos do histórico (`CmdAlterarRepeatedItem`).

**Non-Goals:**
- Não alterar a estrutura de dados Protobuf (`croqui_pb2.Mapa.Referencia`).
- Não alterar os mecanismos de câmera ou outros modos de edição (desenho de rotas, polígonos, etc.).

## Decisions

### 1. Renomeação Completa da Interface (Princípio I)
- **Decisão**:
  - `CardReferencia.btn_linkar` é renomeado/rotulado como `" Vincular Elementos"`, com ícone correspondente.
  - Quando ativado (`checked=True`): texto atualizado para `" Vinculando..."` com fundo azul (`#007bff; color: white;`).
  - Tooltip: `"Vincular ou desvincular elementos (pontos e trajetos) do mapa a esta referência"`.
  - Barra superior de aviso (`WidgetEditorMapas.label_modo`):
    `"MODO VINCULAÇÃO - Clique nos elementos do mapa para vinculá-los ou desvinculá-los desta referência. Elementos vinculados ficam em Ciano."`
- **Alternativas consideradas**:
  - Manter "Linkar POIs": rejeitado por violar o Princípio I e causar confusão para os usuários.
  - "Associar Pontos": menos intuitivo do que "Vincular Elementos", uma vez que o mapa contém não apenas pontos, mas também linhas/trajetos vetoriais.

### 2. Sincronização Unificada de Seleção e Modo de Vinculação
- **Decisão**:
  - Em `PainelReferencias._on_linkar_toggled(True, card)`: invocar `self.selecionar_referencia(card.index)` antes ou junto à emissão do sinal `iniciar_modo_linkagem`.
  - Em `PainelReferencias.selecionar_referencia(index)`: se o modo de vinculação estiver ativo para outro card, desativar o modo de vinculação anterior de forma limpa.
  - Em `WidgetEditorMapas.iniciar_modo_linkagem(idx_ref, ref)`: registrar `self.referencia_selecionada = ref` e `self.referencia_linkagem_ativa = ref`.
- **Alternativas consideradas**:
  - Manter a seleção desvinculada do modo de vinculação: causava descompasso visual (card sem borda azul de seleção enquanto o botão de vincular estava ativo).

### 3. Eliminação de Referência Órfã no Fallback de Destaque
- **Decisão**:
  - Em `WidgetEditorMapas.parar_modo_linkagem()`: garantir que `self.referencia_linkagem_ativa = None` seja definido antes de chamar `self.remover_destaque_pois()`.
  - Em `WidgetEditorMapas.remover_destaque_pois(force=False)`:
    Se a referência ativa de linkagem foi limpa, restaurar o destaque estritamente da `referencia_selecionada` (se houver), sem qualquer efeito colateral de referências antigas.
- **Alternativas consideradas**:
  - Armazenar histórico de referências anteriores: desnecessário e fonte potencial de novos bugs de restauração residual.

### 4. Toggle Reativo Instantâneo no Clique sobre POI
- **Decisão**:
  - Em `WidgetEditorMapas.tratar_clique_poi_linkagem(poi_id)`:
    - Se `poi_id in ref_nova.ids`: remove `poi_id`.
    - Se `poi_id not in ref_nova.ids`: adiciona `poi_id`.
    - Executa o comando no controller (`alterar_referencia`).
    - Atualiza imediatamente `self.linkagem_ref = ref_nova` e `self.referencia_linkagem_ativa = ref_nova`.
    - Executa `self._aplicar_highlight_linkagem()`.
    - Retorna `True` para consumir o evento de clique no item gráfico, impedindo que o evento propague para drag/pan.
- **Alternativas consideradas**:
  - Deixar o redesenho apenas a cargo de sinais reativos assíncronos: pode gerar atraso perceptível de um frame na interface gráfica. A chamada síncrona a `_aplicar_highlight_linkagem()` garante resposta tátil instantânea.

## Risks / Trade-offs

- **[Ciclo de sinais ao reconstruir cards]** → Ao alterar referências no model, `PainelReferencias.carregar_mapa()` reconstrói os cards. Se o botão de vincular emitir `toggled(False)` ao ser destruído ou recriado, o modo poderia ser interrompido indevidamente.
  - *Mitigação*: Uso estrito de `blockSignals(True)` ao restaurar o estado `setChecked(True)` no card recriado, e limpeza controlada apenas por intenção explícita do usuário.
