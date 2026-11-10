# Proposal

## Why

Na primeira coleta real de betas em um croqui completo (*Gruta da Lapinha*, com dezenas de vias), identificamos cinco problemas críticos de desempenho, qualidade de busca, usabilidade e persistência:
1. **Lentidão severa por via (`8s` a `20s+`)**: o buscador recriava conexões TLS a cada consulta, usava `impersonate_os="random"` no `ddgs` (sorteando User-Agents mobile que não batiam com o XPath desktop do Yahoo e disparavam fallbacks em cascata para motores com timeout de `4s–5s` como `html.duckduckgo.com` e `startpage`), baixava o HTML inteiro de até 10 sites sequencialmente por via (`timeout=10s`) e processava apenas 1 escalada por vez.
2. **Baixa precisão e excesso de ruído (90%+ de agregadores/PDFs e zero Instagram)**: incluir o nome técnico do setor (`Setor Gruta - Mapa 3`) e aspas duplas combinadas com `site:` zerava resultados de redes sociais e fazia o buscador retornar quase exclusivamente o PDF do guia antigo no `scribd.com`, além de agregadores de croquis/trilhas (`thecrag.com`, `escaladas.com.br`, `wikiloc.com`) e vídeos sem relação com a via (`match_nome_no_snippet: false`).
3. **Impossibilidade de auditar itens descartados pelo filtro**: candidatos barrados pelos filtros desapareciam silenciosamente, impedindo o curador de inspecionar o que foi descartado na seção **4. Betas Rejeitados** ou restaurar eventuais falsos-negativos.
4. **Quebra de compilação Protobuf por `curadoria_betas.md`**: por ser salvo como `.md` com a chave `escaladas:`, `sanear_uids_croqui` confundia `curadoria_betas.md` com um arquivo `setor_*.md` e injetava campos `uid` inválidos em `CuradoriaBetasEscalada`, quebrando `compilar_croqui` (`Message type "aresta.CuradoriaBetasEscalada" has no field named "uid"`).
5. **Lacunas de UX na Curadoria**: os cards não destacavam claramente a qual via e setor o beta pertencia; o botão `"📋 Copiar Prompt MCP"` não exibia confirmação visual; e o `DialogoColetarBetas` mantinha `"Iniciar Coleta"` e `"Cancelar / Fechar"` após terminar em vez de seguir o ciclo `Iniciar -> Cancelar (com confirmação) -> Finalizar`.

## What Changes

- **Busca Paralela Rápida sem Scrape HTML durante a Coleta (`coleta_de_betas/extratores/blog.py` e `dialogo_coletar_betas.py`)**:
  - Eliminar o download de HTML (`_obter_pagina_processada`) durante a coleta de candidatos, utilizando diretamente o `title` e `body` (snippet) retornados pelo buscador para todas as categorias (mantendo intacta a resolução assíncrona de thumbnails via `ProvedorImagemAresta` na renderização dos cards).
  - Manter cliente HTTP/TLS persistente (*keep-alive*) com User-Agent desktop (`impersonate="chrome"`, `impersonate_os="windows"`) e XPath compatível (`algo-sr | relsrch`), retornando `[]` imediatamente quando a busca não encontrar resultados (`No results found`) sem cascatear para motores lentos/bloqueados.
  - Paralelizar a coleta de escaladas no `WorkerColetaBetas` e as queries de cada escalada via `ThreadPoolExecutor` com cancelamento cooperativo e *pacing* thread-safe.
- **Queries Direcionadas Sanitizadas, Blocklist de Agregadores, Matching Bidirecional de Espaços/Typos e Auditoria em `betas_rejeitados`**:
  - Sanitizar os nomes da via e do pico (`sanitizar_termo_busca`) omitindo o nome técnico do setor (`Setor Mapa X`) e aspas conflitantes, executando 5 buscas identificadas por escalada: **Instagram** (`site:instagram.com`), **YouTube** (`site:youtube.com`), **TikTok** (`site:tiktok.com`), **Facebook** (`site:facebook.com`) e **Geral/Blogs** (aberta).
  - Bloquear domínios agregadores de croquis, PDFs, trilhas e música (`scribd.com`, `ptdocz.com`, `doceru.com`, `thecrag.com`, `escaladas.com.br`, `wikiloc.com`, `mountainproject.com`, `8a.nu`, `27crags.com`, `thetopo.com`, `tripadvisor.*`, `wikipedia.org`, `linktr.ee`, `music.youtube.com`, `/reels/audio/`).
  - Validar relevância exigindo que `título + snippet` mencione o **nome da via** (com matching bidirecional de espaços colapsados, ex.: `"Karrenglass"` $\leftrightarrow$ `"Karren Glass"`, e tolerância a pequenos typos via `SequenceMatcher`) **e** um token significativo do **nome do pico** (ex.: `"lapinha"` para `"Gruta da Lapinha"`).
  - Encaminhar links válidos de posts/vídeos/artigos que forem descartados pelo filtro de precisão ou blocklist para a lista **`betas_rejeitados`** da escalada, incluindo no prefixo do título **de qual request veio** (`instagram`, `youtube`, `tiktok`, `facebook` ou `geral`) e o **motivo do descarte** (ex.: `[Query: geral | Auto-filtrado: domínio bloqueado] ...`), permitindo ao curador auditar na seção **4. Betas Rejeitados** a eficácia de cada query e restaurar qualquer item com 1 clique (com suporte completo a Undo/Redo).
- **BREAKING (Interno): Migração de `curadoria_betas.md` para `curadoria_betas.yaml` e Correção da Compilação**:
  - Atualizar `CroquiModel` (`editor/models/croqui_model.py`), `scripts/preparar_submissao_lib.py` e `scripts/gerenciar_uids_lib.py` para persistir e ler `curadoria_betas.yaml` (YAML puro, sem frontmatter Markdown), impedindo que `sanear_uids_croqui` injete `uid` em `CuradoriaBetasEscalada` e sanitizando campos desconhecidos antes da validação Protobuf.
  - Remover o arquivo corrompido `database/br_mg_lagoa_santa_gruta_da_lapinha/curadoria_betas.md` gerado no teste anterior.
- **Melhorias de UX no `PainelCuradoria` e `DialogoColetarBetas`**:
  - Exibir no topo de cada `CardBetaCuradoria` um badge dedicado de alta visibilidade indicando a **Via** e o **Setor** (`🧗 Via: <nome_escalada> • 📍 <nome_setor>`).
  - Adicionar feedback visual temporário (`"✅ Copiado para a área de transferência!"`) ao clicar no botão `"📋 Copiar Prompt MCP"`.
  - Refatorar os botões do `DialogoColetarBetas` para o fluxo de estados:
    1. *Pronto*: `Cancelar` + `Iniciar Coleta`;
    2. *Coletando*: apenas `Cancelar Coleta` (que pede confirmação ao usuário antes de abortar);
    3. *Concluído*: apenas `Finalizar` (que fecha o diálogo).

## Capabilities

### New Capabilities
<!-- Nenhuma capability nova; expandimos as capabilities existentes de betas. -->

### Modified Capabilities
- `beta-model`: Atualiza a convenção de persistência de `Croqui.curadoria_betas` de `curadoria_betas.md` para `curadoria_betas.yaml`.
- `media-scraping`: Substitui o scraping HTML sequencial por coleta paralela baseada em snippets com queries direcionadas (`site:instagram.com`, `site:youtube.com` e web aberta), sanitização de termos, matching bidirecional de espaços/typos (`Karrenglass` $\leftrightarrow$ `Karren Glass`), blocklist de agregadores e registro de itens descartados como auto-rejeitados para auditoria.
- `curation-panel`: Atualiza a persistência no `CroquiModel` para `curadoria_betas.yaml`, adiciona destaque visual de Via/Setor em `CardBetaCuradoria`, feedback visual no botão de cópia de prompt MCP, injeção de itens auto-filtrados em `betas_rejeitados` via Undo/Redo e fluxo de estados `Iniciar -> Cancelar (com confirmação) -> Finalizar` no `DialogoColetarBetas`.

## Impact

- **`coleta_de_betas/extratores/blog.py` e `blog_test.py`**: Novo motor de busca paralela sem scrape HTML, sanitização de queries, matching simétrico de via/pico, blocklist de agregadores e retorno separado de `(aprovados_filtro, descartados_filtro)`.
- **`coleta_de_betas/curadoria/dialogo_coletar_betas.py` e `dialogo_coletar_betas_test.py`**: Execução paralela de escaladas (`ThreadPoolExecutor`), gravação de candidatos e auto-rejeitados via `CroquiController` (Undo/Redo) e máquina de estados dos botões (`Iniciar` -> `Cancelar Coleta` com confirmação -> `Finalizar`).
- **`coleta_de_betas/curadoria/painel_curadoria.py` e `painel_curadoria_test.py`**: Badge de Via e Setor no `CardBetaCuradoria` e feedback visual no botão `"📋 Copiar Prompt MCP"`.
- **`editor/models/croqui_model.py`, `editor/controllers/croqui_controller.py`, `scripts/preparar_submissao_lib.py` e `scripts/gerenciar_uids_lib.py`**: Migração de `curadoria_betas.md` para `curadoria_betas.yaml` e proteção contra injeção indevida de `uid`.
