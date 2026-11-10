# Design

## Context

Veja `proposal.md` para a motivação completa. Em resumo, ao testar a coleta e a curadoria em um croqui real grande (`br_mg_lagoa_santa_gruta_da_lapinha`, com 132 escaladas), identificamos 4 pontos críticos:
1. Ocultar (`w.hide()`) cards cujo botão `Aprovar`/`Rejeitar` detém foco faz o Qt transferir o foco sequencialmente para cada próximo card abaixo, acionando `QScrollArea.ensureWidgetVisible` dezenas de vezes até jogar o scroll no fundo da página.
2. `PainelCuradoria.atualizar_visualizacao()` reconstrói todos os cards das 4 seções e chama `worker.wait(500)` na thread principal para cada `QThread` de thumbnail em andamento; além disso, `ProvedorImagemAresta` não possui cache em RAM nem cache negativo para URLs sem `og:image`, disparando centenas de `QThread`s repetidas (inclusive para a seção `Betas Rejeitados`).
3. No encerramento da coleta (`132/132`), `_aplicar_lote_coletado` empilha mais de mil `CmdAdicionarRepeated` que emitem `model.repeated_adicionado` sincronicamente, fazendo `WidgetPainelQualidade._ao_mutar_modelo` recalcular `avaliar_nota_qualidade_croqui` mais de mil vezes seguidas na UI thread.
4. No `ExtratorBlog`, compartilhar uma única instância `DDGS()` entre 4 threads durante 660 buscas multiplexadas na mesma conexão HTTP/2 faz o servidor remoto enviar `GOAWAY / ENHANCE_YOUR_CALM` (`h2 connection driver error: connection error detected: detected excessive load generating behavior`).

## Goals / Non-Goals

**Goals:**
- Eliminar completamente o pulo de scroll ao aprovar, rejeitar ou restaurar betas.
- Garantir resposta instantânea (`< 8ms` na UI thread) ao clicar em botões de curadoria e ao concluir a coleta (`132/132`).
- Eliminar o erro `h2 connection driver error` durante coletas longas.
- Reorganizar as 4 seções na ordem lógica da pipeline (`1. Não Scorados`, `2. Não Revisados`, `3. Aprovados`, `4. Rejeitados`) usando cabeçalhos Expando clicáveis (`▼` / `▶`) sem checkboxes.
- Facilitar a conexão MCP na seção `1. Betas Não Scorados` com botão para abrir o `DialogoConexaoMcp`.
- Introduzir aprovação e rejeição em lote por limiar de score (`>= 80%` e `< 80%`) exclusivamente na seção `2. Betas Não Revisados` e alinhar a skill `avaliar_betas_croqui`.

**Non-Goals:**
- Não permitir aprovação em massa na seção `1. Betas Não Scorados` (sem avaliação prévia da LLM).
- Não alterar o schema Protobuf (`beta.proto` / `croqui.proto`).

## Decisions

### 1. Componente `SecaoExpansivelCuradoria` (Expando Clicável + Lazy Rendering)
- **Decisão**: Substituir os 4 `QGroupBox(checkable=True)` por uma classe `SecaoExpansivelCuradoria(QFrame)` com cabeçalho clicável (`QPushButton` flat de largura total exibindo `▼ <Título>` quando expandido e `▶ <Título>` quando recolhido) e um `container_conteudo` que tem sua visibilidade alternada (`setVisible(expandida)`).
- **Ordem das Seções**:
  1. `secao_nao_scorados` (inicia expandida `▼`)
  2. `secao_nao_revisados` (inicia expandida `▼`)
  3. `secao_aprovados` (inicia expandida `▼`)
  4. `secao_rejeitados` (inicia **recolhida `▶` por padrão**).
- **Renderização Sob Demanda (*Lazy*) para Seções Recolhidas**:
  - Se uma seção estiver recolhida (`not secao.esta_expandida()`), `atualizar_visualizacao()` apenas atualiza o título/contador da seção (ex.: `▶  4. Betas Rejeitados - Ignorados em Futuras Coletas (840)`) e marca que os cards daquela seção precisam ser populados quando o usuário clicar para expandi-la.
  - Quando a seção `4. Betas Rejeitados` for expandida pelo usuário, seus cards são instanciados com `carregar_assincrono=False` e `usar_apenas_fallback=True` (sem disparar threads ou requisições HTTP para itens rejeitados).

### 2. Preservação de Scroll e Fim do Bloqueio `worker.wait(500)` na UI Thread
- **Decisão**:
  - Em `PainelCuradoria.atualizar_visualizacao()`, antes de limpar ou atualizar os layouts:
    1. Salvar `valor_scroll = self.scroll_area.verticalScrollBar().value()`.
    2. Se o `QApplication.focusWidget()` for descendente de `self.container_secoes`, limpar seu foco (`focus_w.clearFocus()`) antes de ocultar/remover qualquer card, impedindo que o Qt transfira o foco em cascata (`focusNextPrevChild`) e acione `ensureWidgetVisible` rumo ao fim da página.
    3. Executar a reconstrução com `self.container_secoes.setUpdatesEnabled(False)` e restaurar `self.scroll_area.verticalScrollBar().setValue(valor_scroll)` ao final.
  - Em `CardBetaCuradoria.encerrar_worker()`:
    - Desconectar imediatamente o sinal `imagem_carregada` e conectar `worker.finished.connect(worker.deleteLater)` deixando `self._worker_imagem = None` **sem chamar `wait(500)` na thread principal** (respeitando o Princípio IX do `AGENTS.md`).
  - Em `ProvedorImagemAresta`:
    - Adicionar cache em memória RAM (`self._cache_bytes_ram: dict[str, bytes]` / `self._urls_sem_thumbnail: set[str]`) protegido por `threading.Lock`, para que:
      - URLs já resolvidas na sessão retornem instantaneamente da RAM sem I/O de disco nem rede;
      - URLs que não possuem `og:image` ou falharam fiquem registradas em `self._urls_sem_thumbnail` (cache negativo em memória), retornando o fallback imediatamente sem abrir novas requisições HTTP a cada atualização do painel.
    - Em `CardBetaCuradoria`, se a URL já estiver no cache em RAM ou no cache negativo do `ProvedorImagemAresta` (ou for YouTube já em cache), definir o `QPixmap` diretamente de forma síncrona em `< 0.1ms` **sem nem precisar criar uma `QThread` (`WorkerProvedorImagem`)**!

### 3. Coalescência no `WidgetPainelQualidade` para Eliminar o Congelamento no `132/132`
- **Decisão**:
  - Em `WidgetPainelQualidade` (`editor/views/widget_painel_qualidade.py`), `_ao_mutar_modelo` hoje chama `self.atualizar_painel()` sincronicamente a cada sinal `repeated_adicionado` / `repeated_removido`. Quando `_aplicar_lote_coletado` insere 1.500 itens ao final da coleta, `avaliar_nota_qualidade_croqui` é executado 1.500 vezes seguidas bloqueando a UI.
  - Adicionar coalescência via `QTimer.singleShot(0, self._processar_atualizacao_pendente)` em `WidgetPainelQualidade` (mantendo `atualizar_painel()` público para chamadas diretas síncronas nos testes existentes e conectando `indexChanged` da pilha de undo caso disponível, exatamente como em `PainelCuradoria`).

### 4. Ações em Lote por Score (`Aprovar >= Y%` e `Rejeitar < X%`, Padrão `80%`)
- **Decisão**:
  - Na seção `2. Betas Não Revisados`, incluir uma barra de ações em lote contendo:
    - Um `QSpinBox` (`self.spin_limiar_score`, intervalo `0..100`, sufixo `"%"`, valor padrão **`80`**).
    - Botão **`✅ Aprovar >= 80%`** (`self.btn_aprovar_lote_score`) e botão **`❌ Rejeitar < 80%`** (`self.btn_rejeitar_lote_score`), cujos rótulos mostram também a contagem de itens elegíveis no filtro atual (ex.: `"✅ Aprovar >= 80% (3)"`, `"❌ Rejeitar < 80% (12)"`) e ficam desabilitados quando a contagem é `0`.
  - No `CroquiController`:
    - Adicionar `aprovar_betas_nao_revisados_por_score(score_minimo: int, escalada_uid: str = "") -> int` e `rejeitar_betas_nao_revisados_por_score(score_maximo_exclusivo: int, escalada_uid: str = "") -> int`.
    - Ambos percorrem as escaladas alvo (iterando os índices de trás para frente para não invalidar índices durante a remoção) dentro de um único `iniciar_grupo_undo` / `finalizar_grupo_undo`, garantindo que toda a operação em lote seja revertida com um único `Ctrl+Z`.

### 5. Botão `"🔌 Conectar Agente (MCP)..."` em `1. Betas Não Scorados`
- **Decisão**:
  - No banner de instruções da seção `1. Betas Não Scorados`, atualizar o texto explicativo em 2 passos claros e adicionar o botão `self.btn_conectar_mcp = QPushButton("🔌 Conectar Agente (MCP)...")` ao lado de `self.btn_copiar_prompt_mcp`.
  - `PainelCuradoria` aceita um callback opcional `ao_solicitar_conexao_mcp: Callable[[], Any] | None = None` (ou localiza ` window()._exibir_conexao_mcp` se disponível, com fallback para instanciar `DialogoConexaoMcp(parent=self)`), e `PaginaBetas` em `area_principal.py` injeta `self.window()._exibir_conexao_mcp` ao criar o painel.

### 6. Isolamento de Sessão HTTP/2 por Thread contra `h2 connection driver error`
- **Decisão**:
  - Em `_BuscadorDuckDuckGoPadrao` (`coleta_de_betas/extratores/blog.py`), substituir a instância única compartilhada `self._ddgs` por armazenamento local por thread (`self._local = threading.local()`), mantendo um contador de requisições por thread (`_contagem_reqs`).
  - A cada `MAX_REQS_POR_SESSAO_DDGS = 15` requisições na mesma thread (ou imediatamente se ocorrer qualquer exceção na busca), recriar a instância `DDGS(timeout=self.timeout)` daquela thread. Isso mantém o ganho de *keep-alive* TLS dentro das 5 queries de cada escalada (até 3 escaladas por conexão), mas impede que uma única conexão HTTP/2 acumule centenas de streams simultâneas e dispare `ENHANCE_YOUR_CALM`.

## Risks / Trade-offs

- **[Risk] Testes existentes de `PainelCuradoria` e `WidgetPainelQualidade` que inspecionam seções ou mutações síncronas** → **Mitigação**: Preservar os nomes dos atributos (`secao_nao_scorados`, `secao_nao_revisados`, `secao_aprovados`, `secao_rejeitados`, `cards_nao_scorados`, `cards_nao_revisados`, `cards_aprovados`, `cards_rejeitados`), expor `setTitle()`/`title()` compatíveis em `SecaoExpansivelCuradoria` e garantir que quando `secao_rejeitados` for expandida (ou via método/propriedade) os cards estejam acessíveis.
