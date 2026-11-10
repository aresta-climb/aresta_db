# Design

## Context

Conforme diagnosticado nos testes reais na *Gruta da Lapinha* (ver [proposal.md](./proposal.md)), precisamos resolver simultaneamente a velocidade de coleta, a precisão das queries (eliminando ruído de agregadores/PDFs e capturando Instagram/YouTube com tolerância a variações de grafia), a auditabilidade dos itens descartados em `betas_rejeitados`, a persistência em `curadoria_betas.yaml` (corrigindo o erro de compilação Protobuf) e os ajustes de UX no `PainelCuradoria` e no `DialogoColetarBetas`.

## Goals / Non-Goals

**Goals:**
- Reduzir o tempo de coleta por escalada de `~10s–20s` para sub-segundo em média usando clientes HTTP/TLS persistentes (*keep-alive*), zero download de HTML durante a busca e execução paralela (`ThreadPoolExecutor`) no `WorkerColetaBetas`.
- Maximizar a captura de vídeos e posts reais em primeira mão (**Instagram**, **YouTube**, **TikTok**, **Blogs**) através de queries sanitizadas sem o nome técnico do setor e sem aspas conflitantes.
- Filtrar domínios agregadores (`scribd`, `thecrag`, `escaladas.com.br`, `wikiloc`, etc.) e validar menção simétrica à via (`Karrenglass` $\leftrightarrow$ `Karren Glass` e typos leves) + token do pico, encaminhando os itens descartados para `betas_rejeitados` para inspeção e restauração pelo curador.
- Persistir a curadoria em `curadoria_betas.yaml` via `CroquiModel` (com suporte total a Undo/Redo no `CroquiController`) e garantir que `sanear_uids_croqui` e `compilar_croqui` funcionem sem erros de validação Protobuf.
- Melhorar a UX dos cards (`🧗 Via: ... • 📍 ...`), do botão `"📋 Copiar Prompt MCP"` e do fluxo de botões do `DialogoColetarBetas` (`Iniciar -> Cancelar Coleta (com confirmação) -> Finalizar`).

**Non-Goals:**
- Alterar o funcionamento do `ProvedorImagemAresta`, que já resolve e faz cache offline das thumbnails (`og:image` / YouTube thumbnail) assincronamente na exibição dos cards.

## Decisions

### 1. Cliente Persistente no `_BuscadorDuckDuckGoPadrao` e Paralelismo no `WorkerColetaBetas`
- **Problema**: O `ddgs` instanciava `primp.Client(impersonate="random", impersonate_os="random")` a cada busca. Quando sorteava iOS/Android, o Yahoo devolvia HTML mobile que não batia com o XPath desktop (`relsrch`), lançava `"No results found"` e caía no loop de fallback tentando `duckduckgo` (timeout de `4s–5s`) e `startpage` (`ConnectError` de `3s`).
- **Decisão**:
  - No `_BuscadorDuckDuckGoPadrao`, manter uma instância persistente do motor `Yahoo` (ou `DDGS` configurado com `impersonate="chrome"`, `impersonate_os="windows"` e `items_xpath = "//div[contains(@class, 'algo-sr') or contains(@class, 'relsrch')]"`), protegendo apenas o espaçamento mínimo entre disparos (*pacing* de `~0.15s`) com `threading.Lock`.
  - Se o motor responder sem erro de transporte mas com `0` resultados (`No results found`), retornar `[]` imediatamente sem tentar outros motores em cascata.
  - Em `WorkerColetaBetas`, usar `ThreadPoolExecutor(max_workers=4)` para processar até 4 escaladas simultaneamente com verificação cooperativa de `self._cancelado`.

### 2. Queries Sanitizadas, Matching Simétrico (`Karrenglass` $\leftrightarrow$ `Karren Glass`) e Auditoria em `betas_rejeitados`
- **Sanitização (`sanitizar_termo_busca`) e 5 Queries Identificadas**:
  - Remove indicações de mapa/numeração (`- Mapa 3`, `(Projeto)`, caracteres especiais e aspas) e monta 5 queries identificadas por escalada usando apenas `<via_limpa> <pico_limpo> escalada`:
    1. `instagram`: `<via_limpa> <pico_limpo> escalada site:instagram.com`
    2. `youtube`: `<via_limpa> <pico_limpo> escalada site:youtube.com`
    3. `tiktok`: `<via_limpa> <pico_limpo> escalada site:tiktok.com`
    4. `facebook`: `<via_limpa> <pico_limpo> escalada site:facebook.com`
    5. `geral`: `<via_limpa> <pico_limpo> escalada` (para Blogs reais, Reddit, Twitter/X, etc.)
- **Matching Bidirecional de Espaços e Typos (`menciona_nome_via`)**:
  - Normaliza ambos os lados (`texto_snippet` e `nome_via`) para ASCII minúsculo sem acentos (`norm()`).
  - Verifica se `via_norm in texto_norm` **OU** se `via_norm.replace(" ", "") in texto_norm.replace(" ", "")` (para nomes com $\ge 4$ caracteres sem espaço). Como o colapso de espaços é aplicado nos dois lados, `"Karrenglass"` casa com `"Karren Glass"` e `"Karren Glass"` casa com `"Karrenglass"` de forma 100% simétrica!
  - Caso não haja substring exata, desliza uma janela de tokens pelo `texto_norm` comparando `SequenceMatcher(None, janela_sem_espacos, via_sem_espacos).ratio() >= 0.86` (para vias com $\ge 6$ caracteres), capturando pequenos erros de digitação como `"Karenglass"`.
- **Validação de Contexto Geográfico (`menciona_contexto_pico`)**:
  - Extrai os tokens significativos do `nome_pico` (ignorando stopwords como `"gruta"`, `"pedra"`, `"morro"`, `"serra"`, `"pico"`, `"da"`, `"do"`, `"de"` $\rightarrow$ ex.: `"Gruta da Lapinha"` $\rightarrow$ `{"lapinha"}`). Exige que `título + snippet + url` contenha pelo menos um token significativo do pico.
- **Blocklist de Agregadores e Retorno de Auto-Rejeitados (`buscar_com_rejeitados`)**:
  - Domínios de agregadores de croquis/PDFs/trilhas/música (`scribd.com`, `ptdocz.com`, `doceru.com`, `slideshare.net`, `issuu.com`, `thecrag.com`, `escaladas.com.br`, `wikiloc.com`, `mountainproject.com`, `8a.nu`, `27crags.com`, `thetopo.com`, `tripadvisor.com`, `tripadvisor.com.br`, `wikipedia.org`, `linktr.ee`, `music.youtube.com`) são barrados.
  - Qualquer URL de post/vídeo/artigo específica (não-perfil/login genérico) que seja barrada pela blocklist ou pelo filtro de precisão (`menciona_nome_via` / `menciona_contexto_pico`) é convertida em `beta_pb2.MidiaBeta` com título prefixado indicando a query de origem e o motivo (`"[Query: <origem> | Auto-filtrado: domínio bloqueado] ..."`, `"[Query: <origem> | Auto-filtrado: sem menção à via] ..."` ou `"[Query: <origem> | Auto-filtrado: sem menção ao pico] ..."`) e adicionada em `betas_rejeitados` da escalada via comando `adicionar_betas_rejeitados_lote` no `CroquiController` (dentro do mesmo grupo de Undo `"Coletar Betas"`).

### 3. Persistência em `curadoria_betas.yaml` e Proteção em `sanear_uids_croqui` / `compilar_croqui`
- Em `editor/models/croqui_model.py`:
  - Ao carregar `croqui_msg.curadoria_betas`, suportar leitura de `curadoria_betas.yaml` via `carregar_yaml` (e também ler legado `.md` com frontmatter caso exista em disco, migrando para `curadoria_betas.yaml` ao salvar).
  - Ao salvar em `extrair_arquivos_e_serializar`, gravar sempre `curadoria_betas.yaml` usando `serializar_yaml(..., incluir_cabecalho_spdx=True)` (idêntico ao padrão de `malha_estrada.yaml`) e remover eventual `curadoria_betas.md` antigo.
- Em `scripts/gerenciar_uids_lib.py`:
  - Ajustar a detecção `eh_setor` em `sanear_uids_croqui` para ignorar explicitamente arquivos `curadoria_betas*`.
- Em `scripts/preparar_submissao_lib.py`:
  - Ler `curadoria_betas.yaml` por padrão e sanitizar os itens de `escaladas` removendo eventual chave espúria `uid` antes de chamar `json_format.ParseDict`.

### 4. UX do Card, Botão MCP e Diálogo de Coleta
- **`CardBetaCuradoria`**: adiciona `self.label_via_setor = QLabel(...)` no topo do card com estilo destacado (`🧗 Via: <nome_escalada>  •  📍 <nome_setor>`), mantendo `self.label_titulo` apenas com o título limpo da mídia.
- **`PainelCuradoria._copiar_prompt_mcp`**: altera temporariamente o texto do botão para `"✅ Copiado para a área de transferência!"` e restaura após `2000ms` via `QTimer.singleShot`.
- **`DialogoColetarBetas`**:
  - Estado `pronto`: `btn_cancelar` (`"Cancelar"`, visível) + `btn_iniciar` (`"Iniciar Coleta"`, visível) + `btn_finalizar` (`"Finalizar"`, oculto).
  - Estado `coletando`: `btn_iniciar` oculto, `btn_cancelar` com texto `"Cancelar Coleta"`. Clicar em `"Cancelar Coleta"` exibe `QMessageBox.question` confirmando o cancelamento.
  - Estado `concluido`: `btn_iniciar` e `btn_cancelar` ocultos; `btn_finalizar` (`"Finalizar"`) visível e focado, conectado a `self.accept()`.

## Risks / Trade-offs

- **[Risco] Acúmulo de itens auto-filtrados em `betas_rejeitados`** $\rightarrow$ **Mitigação**: Apenas URLs válidas de posts/vídeos/artigos (e não homepages ou páginas de login/perfil genérico) entram em `betas_rejeitados`, deduplicadas por URL canônica e limitadas aos resultados reais da busca, servindo também para bloquear reprocessamento futuro e permitir restauração com 1 clique.
