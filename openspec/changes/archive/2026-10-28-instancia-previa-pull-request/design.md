# Design

## Context

Veja `proposal.md` para a motivação e o escopo funcional.
Atualmente:
- Em `aresta_db`, o script `serving/pr_db_validator.py` compila os croquis modificados de uma Pull Request usando `deploy(..., is_producao=False)` em um `tempfile.TemporaryDirectory()` e descarta o resultado, postando um comentário simples via `gh pr comment` em `.github/workflows/pr-db-validator.yml`.
- Em `serving/update_serving.py`, já temos a infraestrutura de upload paralelo (`boto3`) para o bucket Cloudflare R2 `aresta-serving` exposto publicamente em `https://serving.arestaclimb.com`.
- Em `aresta_backend/cloudflare/previa`, o Worker `previa.arestaclimb.com` gerencia sessões ao vivo do Editor Desktop usando `SessaoDurableObject` e WebSockets (`/ws` e `/<codigo>/events`), além de servir `/.well-known/assetlinks.json` e `/.well-known/apple-app-site-association`.
- Em `aresta_app/frontend`, os arquivos nativos (`AndroidManifest.xml`, `Runner.entitlements` e `Info.plist`) já declaram suporte a App Links / Universal Links para `previa.arestaclimb.com` e `aresta://previa`, mas `DeepLinkNavigatorService` ainda não roteia esses links para `conectarEditor()`, e `EditorDeCroqui` aceita apenas códigos de exatos 8 caracteres e tenta reconectar ao WebSocket `/<codigo>/events` a cada 4 segundos caso a conexão falhe.

## Goals / Non-Goals

**Goals:**
- Estruturar toda a lógica nova em `aresta_db` como bibliotecas independentes (Library-First), 100% em português brasileiro, com espelhamento 1:1 de testes (`*_test.py`), 100% de cobertura comportamental e Fakes determinísticos para fronteiras externas (R2/S3 e GitHub API), em conformidade estrita com `AGENTS.md`.
- Eliminar qualquer custo ou estado de Durable Objects no Cloudflare Worker para prévias de Pull Requests, operando como proxy *stateless* para `serving.arestaclimb.com/pr/<id>/`.
- Garantir retrocompatibilidade imediata com versões já publicadas do aplicativo móvel para PRs de até 6 dígitos (`pr00-0042` -> 8 caracteres) e escalabilidade *unbounded* (`>= 8` caracteres) para o futuro.
- Produzir um `resumo.html` rico, autocontido e rápido no Python durante a execução da Action, capaz de exibir diffs de mapas (com `<svg>` vetorial e modos Lado a Lado / Slider quando a foto mudar), diffs de imagens de capa/thumbnail/Markdown (usando cópias `_base` no R2) e diffs estruturais pareados por `uid`.

**Non-Goals:**
- Manter conexões WebSocket de *Live Reload* ativas para instâncias de Pull Request (atualizações em PR ocorrem a cada novo `git push` na branch).
- Realizar diff de Protobuf ou renderização de imagens dentro do Cloudflare Worker em TypeScript (toda a computação pesada ocorre no runner do GitHub Actions em Python).

## Decisions

### 1. Arquitetura Modular em `serving/` (Library-First e Fakes Determinísticos)
- **Decisão**: Dividir a responsabilidade em três bibliotecas coesas e independentes dentro de `serving/`:
  1. `serving/diff_croqui_pr_lib.py` (+ `serving/diff_croqui_pr_lib_test.py`): Recebe o diretório/dados compilados da branch base (`main`) e da branch da PR e produz um modelo de dados estruturado (`ResumoDiffPullRequest`) pareado por `uid` (para Picos, Grupos, Setores, Escaladas, Mapas e Pontos de Interesse) e por caminho/SHA-256 (para imagens de mapa, capa, thumbnail, Markdown e anexos).
  2. `serving/renderizador_resumo_pr_lib.py` (+ `serving/renderizador_resumo_pr_lib_test.py`): Biblioteca pura que recebe `ResumoDiffPullRequest` e os metadados da PR (número, commit, URL base do serving) e gera:
     - O documento autocontido `resumo.html` (CSS/JS inline, dark mode, camada `<svg>` interativa sobre mapas, comparador Lado a Lado / Slider Cortina para imagens alteradas e QR Code em SVG inline);
     - O texto Markdown enxuto para o comentário da PR (incluindo a assinatura invisível `<!-- aresta-pr-validator -->`).
  3. `serving/publicador_pr_r2_lib.py` (+ `serving/publicador_pr_r2_lib_test.py`) e `serving/cliente_r2_fake.py` (+ `serving/cliente_r2_fake_test.py`): Gerencia a sincronização dos artefatos compilados da PR, das imagens base modificadas/deletadas (`pr/<id>/_base/...`) e do `resumo.html` para `s3://aresta-serving/pr/<id>/`, bem como a exclusão em lote (`limpar_pasta_pr_r2`) quando a PR é fechada.
- **Racional**: Isola completamente o cálculo de diff, a geração de HTML/Markdown e o I/O de rede (R2), permitindo testar 100% dos cenários de negócio com Fakes em memória sem mocks de código interno (`AGENTS.md`, Princípios II, III, IV e V).

### 2. Esquema de Código `pr*` Unbounded (`>= 8` caracteres)
- **Decisão**:
  - Codificar a Pull Request de número $N$ como `f"pr{N:06d}"` (ex: PR `#42` $\rightarrow$ `pr000042`, formatado como `pr00-0042`; PR `#1234567` $\rightarrow$ `pr1234567`, formatado como `pr12-34567`).
  - Atualizar `editor/core/codigo_sessao.py`, `aresta_backend/cloudflare/previa/src/gerenciador_sessao.ts` e `aresta_app/frontend/lib/services/editor_croqui.dart` para validar códigos com `len(limpo) >= 8` e extrair o número da PR via regex `^pr0*([1-9]\d*)$`.
  - No `gerarCodigoUnico` do Worker (e em validações de sessão de editor), rejeitar/resortear qualquer código aleatório que comece com `"pr"`.
- **Alternativas consideradas**:
  - *Usar rota `/pr/42` no lugar de código*: Quebraria a compatibilidade imediata com os aplicativos já instalados hoje, que validam códigos de 8 caracteres Base36 no diálogo "Conectar Editor" e no scanner de QR Code.

### 3. Proxy Stateless no Worker `previa.arestaclimb.com` e Rota `/resumo/<codigo_pr>`
- **Decisão**:
  - Na entrada do `fetch` do Worker `aresta_backend/cloudflare/previa/src/index.ts`, antes de acionar `env.SESSAO_DO`:
    1. Se a rota for `GET /resumo/<codigo_pr>` e `<codigo_pr>` for um código de PR válido (`pr*`), fazer `fetch("https://serving.arestaclimb.com/pr/<numero_pr>/resumo.html")` e retornar com `Content-Type: text/html; charset=utf-8`.
    2. Se o primeiro segmento da rota for um código de PR (`/<codigo_pr>` ou `/<codigo_pr>/<subcaminho>`):
       - Para `/<codigo_pr>` (sem subcaminho, acesso via navegador desktop): exibir a Landing Page HTML da PR contendo também um botão em destaque para abrir `/resumo/<codigo_pr>`.
       - Para `/<codigo_pr>/info` ou `/<codigo_pr>/meta`: retornar HTTP 200 com `{ codigo, metadados: {}, local_url: null }`.
       - Para `/<codigo_pr>/events`: retornar HTTP 404 (sem WebSocket).
       - Para `/<codigo_pr>/<arquivo>`: fazer proxy de `https://serving.arestaclimb.com/pr/<numero_pr>/<arquivo>`, repassando cabeçalhos de cache (`If-None-Match` / `ETag`) e CORS.
  - Em `/.well-known/apple-app-site-association`, adicionar `{ "/": "/resumo/*", "exclude": true }` e `"NOT /resumo/*"` para que o iOS abra `/resumo/*` sempre no Safari.
  - No Android (`AndroidManifest.xml` e `DeepLinkNavigatorService`), restringir/desviar `/resumo/*` para abertura no navegador externo (`LaunchMode.externalApplication`), mantendo `/<codigo>` abrindo diretamente no aplicativo.

### 4. Comparação de Imagens e Armazenamento Seletivo de `_base`
- **Decisão**:
  - Durante a validação da PR no GitHub Actions, para obter o estado base sem precisar compilar o repositório inteiro na `main`, o validador lê os dados da branch base (`origin/main`) apenas para as pastas modificadas na PR (via `git worktree` temporário ou extração pontual da árvore de `origin/main` para `database/<id>` e `generated/<id>`).
  - Quando uma imagem `.webp` (de mapa, capa, thumbnail ou Markdown) existir na base e tiver sido modificada (SHA-256 diferente) ou removida na PR, a imagem original da base é copiada para o diretório de saída em `_base/<id>/<caminho_relativo>` e enviada para `s3://aresta-serving/pr/<numero_pr>/_base/<id>/<caminho_relativo>`.
  - No `resumo.html`, imagens inalteradas apontam diretamente para `https://serving.arestaclimb.com/pr/<numero_pr>/<id>/imagens/...`, e o lado "Antes" de imagens modificadas/removidas aponta para `https://serving.arestaclimb.com/pr/<numero_pr>/_base/<id>/imagens/...`.
- **Racional**: Funciona de forma determinística tanto para croquis já publicados quanto para croquis com `publicar_croqui: false` na `main`, adicionando overhead quase nulo de armazenamento (apenas as imagens cujos pixels mudaram na PR são duplicadas em `_base/`).

### 5. Comentário Único no Final da PR ("Delete & Recreate")
- **Decisão**:
  - No step de comentário de `.github/workflows/pr-db-validator.yml`, utilizar `gh api` para listar os comentários da issue/PR, filtrar aqueles cujo `body` contenha `<!-- aresta-pr-validator -->`, deletá-los (`DELETE /repos/{owner}/{repo}/issues/comments/{id}`) e em seguida criar um novo comentário (`gh pr comment`).
- **Racional**: Garante que a PR nunca acumule dezenas de comentários repetidos a cada commit e que o comentário com os links da prévia esteja sempre visível no final da página, logo após o último commit.

## Risks / Trade-offs

- **[Risco] PRs abandonadas sem fechamento explícito mantendo arquivos no R2** $\rightarrow$ *Mitigação*: Além do job `cleanup-pr` disparado em `pull_request: types: [closed]`, configurar regra de ciclo de vida (Object Lifecycle Rule) no bucket `aresta-serving` para expirar objetos com prefixo `pr/` após 30 dias.
- **[Risco] Segredos do R2 em PRs vindas de forks externos** $\rightarrow$ *Mitigação*: No GitHub Actions, segredos de escrita no R2 só estão disponíveis em PRs de branches do próprio repositório (que é o fluxo padrão do Editor Desktop Aresta e dos colaboradores). Se as credenciais do R2 não estiverem presentes no ambiente (ex: fork externo sem segredos), o `pr_db_validator.py` executa a validação normalmente e apenas pula a etapa de upload para o R2, registrando o aviso no comentário.
