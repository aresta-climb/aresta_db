# Proposal

## Why

Ao coletar e revisar candidatos de betas em croquis de grande porte (como a Gruta da Lapinha, com 132 escaladas e 5 queries por via), surgiram quatro problemas críticos de fluidez, estabilidade HTTP/2 e usabilidade no `PainelCuradoria`:
1. **Pulo de scroll para o final da página ao aprovar/rejeitar**: chamar `w.hide()` nos cards com botão focado dispara uma cascata de transferência de foco do Qt (`focusNextPrevChild` + `QScrollArea.ensureWidgetVisible`) que rola a página inteira até o último card de `Betas Rejeitados`.
2. **Lag de vários segundos em cada clique e travamento no final da coleta (`132/132`)**: `atualizar_visualizacao()` destrói e recria todos os cards das 4 seções a cada ação, bloqueia a UI thread com `worker.wait(500)`, dispara centenas de `QThread`s de thumbnail sem cache em RAM/cache negativo (inclusive para itens rejeitados) e emite milhares de sinais `repeated_adicionado` síncronos que recalculam `WidgetPainelQualidade` repetidamente na thread principal.
3. **Erro `h2 connection driver error: detected excessive load generating behavior` (`ENHANCE_YOUR_CALM`)**: o compartilhamento de uma única instância `DDGS()` multiplexada em HTTP/2 entre 4 threads abertas para 660 queries consecutivas aciona proteção anti-flood na conexão HTTP/2 do `primp`.
4. **Ergonomia do pipeline de curadoria**: a seção de `Betas Não Scorados` deve ser a primeira do painel (seguindo a ordem lógica da pipeline), com instruções claras e botão direto para abrir o `DialogoConexaoMcp`; as seções devem usar cabeçalho Expando clicável (`▼` / `▶`) em vez de checkboxes de `QGroupBox`; e a seção `Betas Não Revisados` (já pontuada pela LLM) precisa de ações em lote baseadas no score (`Aprovar >= 80%` e `Rejeitar < 80%`) alinhadas à calibração da skill `avaliar_betas_croqui`.

## What Changes

- **Ordem de Pipeline e Seções Expando Clicáveis (`▼` / `▶`)**:
  - Reordenar as 4 seções do `PainelCuradoria` para refletir o fluxo de trabalho:
    1. `1. Betas Não Scorados (Aguardando Avaliação LLM)`
    2. `2. Betas Não Revisados (Avaliados pelo LLM)`
    3. `3. Betas Aprovados (Publicados na Escalada)`
    4. `4. Betas Rejeitados (Ignorados em Futuras Coletas)` (iniciando recolhida `▶` por padrão com renderização *lazy* sob demanda).
  - Substituir `QGroupBox.setCheckable(True)` (que exibia um checkbox enganoso que apenas desabilitava os widgets) por um componente `SecaoExpansivelCuradoria` onde clicar no título abre/fecha (`▼` / `▶`) o conteúdo.
- **Conexão MCP Facilitada em `Betas Não Scorados`**:
  - Atualizar o banner de instruções em `1. Betas Não Scorados` com passo a passo claro em 2 etapas e dois botões de ação: **`🔌 Conectar Agente (MCP)...`** (que abre o wizard `DialogoConexaoMcp` existente na `JanelaPrincipal`) e **`📋 Copiar Prompt MCP`** (com feedback visual `"✅ Copiado para a área de transferência!"`).
- **Ações em Lote por Score da LLM (`>= 80%` e `< 80%`) e Calibração da Skill**:
  - Adicionar na seção `2. Betas Não Revisados` controles de ação em lote baseados exclusivamente no `llm_confidence_score` (limiar configurável via `QSpinBox` com valor padrão **`80`**): **`✅ Aprovar >= 80%`** e **`❌ Rejeitar < 80%`**, executados atomicamente em um único comando Undo/Redo (`CmdMacro`) no `CroquiController`.
  - Atualizar `.agents/skills/avaliar_betas_croqui/SKILL.md` documentando que notas `>= 80` são elegíveis para aprovação em lote automática pelo revisor e jamais devem ser atribuídas a agregadores de PDF/guias antigos (ex.: Scribd), homônimos ou menções vagas.
- **Eliminação do Pulo de Scroll, Lag de Cliques e Travamento no Final da Coleta (`132/132`)**:
  - Preservar a posição vertical do `QScrollArea` e limpar o foco do card antes de ocultar/remover widgets em `PainelCuradoria`, eliminando o salto de scroll para o final da página.
  - Remover `worker.wait(500)` da thread principal em `CardBetaCuradoria.encerrar_worker()`, adicionar cache em memória RAM (`dict[str, QPixmap]`) e cache negativo de falhas em `ProvedorImagemAresta`, limitar concorrência de downloads de thumbnail e usar diretamente o pixmap de fallback instantâneo na seção `4. Betas Rejeitados` (sem disparar HTTP GET para itens descartados).
  - Adicionar coalescência assíncrona (`QTimer.singleShot(0)`) em `WidgetPainelQualidade._ao_mutar_modelo` para não recalcular `avaliar_nota_qualidade_croqui` milhares de vezes sincronicamente durante macros em lote.
- **Isolamento de Sessão HTTP/2 por Thread e Renovação Periódica contra Erro `h2`**:
  - Em `_BuscadorDuckDuckGoPadrao` (`coleta_de_betas/extratores/blog.py`), isolar a instância `DDGS()` por thread (`threading.local()`) com renovação periódica da sessão a cada lote de buscas e espaçamento leve entre queries para evitar o erro `h2 connection driver error: detected excessive load generating behavior` (`ENHANCE_YOUR_CALM`).

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability: evolução de capabilities existentes -->

### Modified Capabilities
- `curation-panel`: Reordenação das 4 seções (Não Scorados primeiro), substituição de checkboxes por cabeçalhos Expando clicáveis (`▼`/`▶`) com `Betas Rejeitados` recolhido e *lazy* por padrão, botão para abrir o wizard `DialogoConexaoMcp`, ações em lote por limiar de score (`Aprovar >= 80%` e `Rejeitar < 80%`) na seção `Betas Não Revisados`, preservação de scroll/foco e eliminação de bloqueios na UI thread.
- `media-scraping`: Isolamento de sessão `DDGS` por thread (`threading.local()`) com renovação periódica contra flood HTTP/2 (`h2 connection driver error`), cache em RAM e cache negativo em `ProvedorImagemAresta` e dispensa de requisições HTTP de thumbnail para itens rejeitados.
- `avaliador-betas-subagente`: Atualização da skill `avaliar_betas_croqui` com a régua de calibração explícita para o limiar `>= 80` de aprovação em lote e penalização severa (`< 30`) para agregadores e PDFs de guias antigos.

## Impact

- `coleta_de_betas/curadoria/painel_curadoria.py` e `coleta_de_betas/curadoria/painel_curadoria_test.py`
- `coleta_de_betas/curadoria/provedor_imagem_aresta.py` e `coleta_de_betas/curadoria/provedor_imagem_aresta_test.py`
- `coleta_de_betas/extratores/blog.py` e `coleta_de_betas/extratores/blog_test.py`
- `editor/controllers/croqui_controller.py` e `editor/controllers/croqui_controller_test.py`
- `editor/legacy_views/area_principal.py` e `editor/views/widget_painel_qualidade.py`
- `.agents/skills/avaliar_betas_croqui/SKILL.md`
