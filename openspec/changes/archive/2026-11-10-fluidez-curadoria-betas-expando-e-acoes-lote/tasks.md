# Tasks

## 1. Isolamento de Sessão HTTP/2 e Cache de Thumbnails (`ProvedorImagemAresta` e `ExtratorBlog`)

- [x] 1.1 Em `coleta_de_betas/extratores/blog.py` e `coleta_de_betas/extratores/blog_test.py`, isolar a instância `DDGS()` por thread (`threading.local()`) com renovação automática de sessão a cada lote de requisições (`MAX_REQS_POR_SESSAO_DDGS`) ou em falha de conexão para eliminar o erro `h2 connection driver error: detected excessive load generating behavior`, verificando com `uv run pytest coleta_de_betas/extratores/blog_test.py -n 0 -v`.
- [x] 1.2 Em `coleta_de_betas/curadoria/provedor_imagem_aresta.py` e `coleta_de_betas/curadoria/provedor_imagem_aresta_test.py`, adicionar cache em memória RAM e cache negativo de URLs sem thumbnail (`tem_resultado_imediato` / `obter_pixmap_imediato`), evitando repetir chamadas HTTP para páginas sem `og:image`, verificando com `uv run pytest coleta_de_betas/curadoria/provedor_imagem_aresta_test.py -n 0 -v`.

## 2. Ações em Lote no `CroquiController` e Coalescência no `WidgetPainelQualidade`

- [x] 2.1 Em `editor/controllers/croqui_controller.py` e `editor/controllers/croqui_controller_test.py`, implementar `aprovar_betas_nao_revisados_por_score(score_minimo, escalada_uid)` e `rejeitar_betas_nao_revisados_por_score(score_maximo_exclusivo, escalada_uid)` empilhando um único grupo Undo/Redo (`CmdMacro`), verificando com `uv run pytest editor/controllers/croqui_controller_test.py -n 0 -k "curadoria or score" -v`.
- [x] 2.2 Em `editor/views/widget_painel_qualidade.py` e `editor/views/widget_painel_qualidade_test.py`, coalescer as atualizações reativas de `_ao_mutar_modelo` com `QTimer.singleShot(0)` (e sincronização com `indexChanged` do histórico) para não recalcular `avaliar_nota_qualidade_croqui` milhares de vezes sincronicamente no final da coleta (`132/132`), verificando com `uv run pytest editor/views/widget_painel_qualidade_test.py -n 0 -v`.

## 3. Painel de Curadoria Fluido, Expando Clicável, Conexão MCP e Skill `avaliar_betas_croqui`

- [x] 3.1 Em `coleta_de_betas/curadoria/painel_curadoria.py`, `coleta_de_betas/curadoria/painel_curadoria_test.py` e `editor/legacy_views/area_principal.py`, reordenar as 4 seções (`1. Não Scorados`, `2. Não Revisados`, `3. Aprovados`, `4. Rejeitados`), substituir `QGroupBox` por `SecaoExpansivelCuradoria` (cabeçalho Expando clicável `▼`/`▶`, com `4. Betas Rejeitados` iniciando recolhida e *lazy* sem requisições HTTP de thumbnail), adicionar o botão `"🔌 Conectar Agente (MCP)..."` em `1. Betas Não Scorados`, adicionar a barra de lote (`✅ Aprovar >= 80%` e `❌ Rejeitar < 80%` com `QSpinBox` padrão `80`) em `2. Betas Não Revisados`, remover `worker.wait(500)` da UI thread e preservar a posição vertical do scroll (`verticalScrollBar().value()`) ao aprovar/rejeitar, verificando com `uv run pytest coleta_de_betas/ -n 0 -v`.
- [x] 3.2 Atualizar `.agents/skills/avaliar_betas_croqui/SKILL.md` documentando a régua de calibração para aprovação automática em lote (`>= 80` exclusivo para betas reais em primeira mão da via no pico; `< 30` para páginas agregadoras/PDFs como Scribd) e validar `ruff check` e `mypy coleta_de_betas/`.
