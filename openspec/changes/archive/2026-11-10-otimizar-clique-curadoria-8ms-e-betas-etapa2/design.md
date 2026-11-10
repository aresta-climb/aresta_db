# Design

## Context

Veja `proposal.md` para a motivação e o perfilamento (`cProfile`) na Gruta da Lapinha (`3029.9 ms` por clique individual em `PainelCuradoria` e discrepância na avaliação de `curadoria_betas` em `avaliador_nota_qualidade.py`).

## Goals / Non-Goals

**Goals:**
- Reduzir o tempo de execução do clique individual em **Aprovar**, **Rejeitar** ou **Restaurar** na aba **Betas** (incluindo `CroquiController` + atualização visual + `QApplication.processEvents()`) de `~3030 ms` para `< 8 ms` na média.
- Mover a tarefa **"Vídeos de beta e curadoria em dia"** para a **Etapa 2 (`100 pontos`, `etapa2_videos_betas`)** e verificar pendências reais em `curadoria_betas` (`betas_nao_scorados` e `betas_nao_revisados`), além de manter retrocompatibilidade caso exista `betas_pendentes.binarypb`.

**Non-Goals:**
- Alterar o schema Protobuf de `beta.proto` ou `croqui.proto`.

## Decisions

### 1. Reconciliação Incremental, Construção em Fatias (*Time-Sliced*) e Folha de Estilo Centralizada em `PainelCuradoria`
- **Decisão**:
  - Em vez de destruir todos os `CardBetaCuradoria` e recriá-los do zero a cada mutação em `atualizar_visualizacao()`, manteremos um pool/reconciliação de cards por chave imutável de conteúdo `(secao, escalada_uid, idx_ou_url, score_llm)` e atualizaremos os cards existentes in-place (`atualizar_acoes(...)`), removendo do layout apenas os cards que deixaram a seção.
  - Quando houver mais novos cards para instanciar do que o orçamento de uma fatia (`TAMANHO_FATIA_CARDS_PADRAO = 5` no modo assíncrono), `atualizar_visualizacao()` instancia imediatamente a primeira fatia (preenchendo o topo visível do `QScrollArea`) e agenda a criação das fatias seguintes via `QTimer.singleShot(0, self._processar_proxima_fatia_cards)`, mantendo cada fatia abaixo de `8 ms`.
  - Em `CardBetaCuradoria`:
    - Remover `setWordWrap(True)` dos `QLabel`s e definir altura fixa `setFixedHeight(112)`, eliminando o cálculo recursivo `heightForWidth` do `QBoxLayout` dentro do `QScrollArea` (que consumia `2591 ms` em C++ durante `processEvents()`).
    - Substituir as 9 chamadas `setStyleSheet()` individuais por card por uma única folha de estilo aplicada no `PainelCuradoria` usando seletores de classe e `objectName` (`#LabelViaSetor`, `#LabelFonteBeta`, `#BtnAprovarBeta`, `#BtnRejeitarBeta`, `#BtnRestaurarBeta`).
  - Em `coleta_de_betas/curadoria/dialogo_coletar_betas.py`, importar `ExtratorBlog` (`ddgs` / `bs4`) apenas dentro de `criar_extratores_padrao()` para não penalizar a abertura da aba Betas.

### 2. Cache em RAM Estrito e Pool de 4 Worker Threads em `ProvedorImagemAresta`
- **Decisão**:
  - `obter_pixmap_imediato` consulta **exclusivamente a memória RAM** (`_cache_pixmap_ram`, `_cache_bytes_ram` e `_urls_sem_thumbnail`) em $O(1)$, sem tocar o sistema de arquivos (`is_file()` / `read_bytes()`) na UI thread.
  - Para carregamento assíncrono de thumbnails (disco ou HTTP), `ProvedorImagemAresta` mantém um `ThreadPoolExecutor(max_workers=MAX_WORKERS_THUMBNAIL)` com **`MAX_WORKERS_THUMBNAIL = 4` worker threads**, decodificando `QImage` nas threads de background e emitindo sinal Qt para converter `QPixmap.fromImage` na thread principal e notificar os callbacks registrados (`solicitar_pixmap_assincrono` / `cancelar_callback_assincrono` / `encerrar_workers`).

### 3. Endereçamento $O(1)$ em `comandos_protobuf.py` e `CroquiController`
- **Decisão**:
  - Em `navegar_para_alvo` (`editor/commands/comandos_protobuf.py`), se o primeiro segmento do caminho (`prefixo`) já for um campo direto do `root_msg` (`prefixo in root_msg.DESCRIPTOR.fields_by_name`, como `curadoria_betas` ou `picos`), navegar imediatamente via `navegar_para_mensagem(root_msg, alvo_limpo)` em $O(1)$, sem varrer os `3140` nós da árvore em `_buscar_mensagem_por_uid`.
  - Em `CroquiController._garantir_curadoria_escalada`, `aprovar_beta_curadoria`, `rejeitar_beta_curadoria` e `restaurar_beta_rejeitado`, usar o caminho string `"curadoria_betas.conteudo.escaladas.<idx>"` nos comandos `CmdRemoverRepeated` e `CmdAdicionarRepeated`, evitando que `validar_pertence_ao_croqui` chame `resolver_alvo_mensagem` ($O(N)$) para um `CuradoriaBetasEscalada` (que não tem `uid` próprio).

### 4. Suspensão de Recálculo em Abas Ocultas (`WidgetPainelQualidade` e `WidgetEditorDados`)
- **Decisão**:
  - Em `WidgetPainelQualidade._processar_atualizacao_pendente`, se `not self.isVisible()`, manter `self._atualizacao_pendente = True` e executar `atualizar_painel()` dentro de `showEvent(event)` quando o usuário exibir a aba **Painel** (quando o widget não tiver pai/janela visível em testes unitários headless, continuar atualizando normalmente).
  - Em `WidgetEditorDados._on_repeated_adicionado` e `_on_repeated_removido`, ignorar imediatamente sinais cujo `campo_nome` pertença exclusivamente à curadoria de betas (`betas_nao_scorados`, `betas_nao_revisados`, `betas_rejeitados`).

### 5. Tarefa "Vídeos de beta e curadoria em dia" na Etapa 2 (`100 pts`)
- **Decisão**:
  - Em `editor/core/avaliador_nota_qualidade.py`, mover a tarefa de betas da Etapa 3 (`10 pts`, `etapa3_videos_betas`) para a **Etapa 2 (`100 pts`, `etapa2_videos_betas`)**:
    - Etapa 2 passa a ter 8 tarefas de `100` pontos (`800` pontos máximos).
    - Etapa 3 passa a ter 6 tarefas de `10` pontos (`60` pontos máximos).
    - A verificação `tem_beta_pendente` consulta `_resolver_arquivo_md(dados.get("curadoria_betas"), croqui_path, cache_md)` somando `len(esc.get("betas_nao_scorados") or []) + len(esc.get("betas_nao_revisados") or [])` para cada entrada em `escaladas` (além de checar `(croqui_path / "betas_pendentes.binarypb").is_file()`).

## Risks / Trade-offs

- **[Risk]** Testes existentes de `avaliador_nota_qualidade_test.py` e `widget_painel_qualidade_test.py` verificam a pontuação total (`nota_maxima` de `8770` passa para `8860`) e o `id_tarefa` de betas → **Mitigation**: Atualizar os testes unitários correspondentes para refletir os `100` pontos da Etapa 2 (`etapa2_videos_betas`) e adicionar teste específico para pendências em `curadoria_betas`.
