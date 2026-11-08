# Tasks

## 1. Unificação do Remote `origin` na Sincronização Git (`aresta_db`)

- [x] 1.1 Refatorar os testes de `configurar_remotes`, `fazer_fetch` e `fazer_checkout_main_upstream` em `editor/core/sync_test.py` (usando repositórios `pygit2` reais em `tmp_path` sem mocks internos) para exigir configuração exclusiva do remote `origin`, remoção automática dos remotes `upstream` e `proxy` e checkout a partir de `refs/remotes/origin/main`, verificando a falha inicial (Red) via `uv run pytest editor/core/sync_test.py`
- [x] 1.2 Atualizar `GerenciadorSincronizacao` em `editor/core/sync.py` e logs/comentários em `editor/core/worker.py` (`editor/core/worker_test.py`) para manter apenas o remote `origin`, remover `upstream` e `proxy` em `configurar_remotes()`, buscar apenas `origin` em `fazer_fetch()` e realizar checkout a partir de `origin/main`, verificando 100% de aprovação e cobertura com `uv run pytest editor/core/sync_test.py editor/core/worker_test.py`

## 2. Base `origin/main` e Detecção de Falha de Referência no Push (`aresta_db`)

- [x] 2.1 Adicionar testes em `editor/core/servico_submissao_test.py` verificando que `_obter_commit_base` utiliza `refs/remotes/origin/main` e que `fazer_push_proxy` lança `ErroSubmissao` (reportando ao Sentry na etapa `push_proxy`) quando `CallbacksProxy.push_update_reference` recebe mensagem de erro não nula (`ng refs/heads/...`), atualizando as fixtures de `servico_submissao_test.py`, `integracao_submissao_proxy_test.py` e `sincronizacao_pr_integracao_test.py` para `refs/remotes/origin/main` e verificando a falha inicial (Red)
- [x] 2.2 Implementar `push_update_reference` em `CallbacksProxy` e atualizar `_obter_commit_base` e `fazer_push_proxy` em `editor/core/servico_submissao.py`, verificando aprovação e 100% de cobertura com `uv run pytest editor/core/servico_submissao_test.py editor/core/integracao_submissao_proxy_test.py editor/core/sincronizacao_pr_integracao_test.py`

## 3. Inspeção de `report-status` no `git-proxy` e Diagnóstico 404 no `create-pr` (`aresta_backend`)

- [x] 3.1 Escrever testes em `supabase/functions/compartilhado/analisador_pkt_line_test.ts` para `extrairErrosResultadoReceivePack` (cobrindo respostas `pkt-line` diretas e encapsuladas em `side-band-64k` com `unpack ok` + `ok refs/heads/...`, `unpack error` e `ng refs/heads/...`) e implementar a função em `supabase/functions/compartilhado/analisador_pkt_line.ts`, verificando com `deno test supabase/functions/compartilhado/analisador_pkt_line_test.ts`
- [x] 3.2 Escrever testes em `supabase/functions/git-proxy/index_test.ts` garantindo que `git-proxy` só registra nova branch em `sugestoes_branches` após confirmação de sucesso do `git-receive-pack` e reporta ao Sentry recusas `ng refs/heads/...` ou `unpack` no stream `pkt-line`, implementando o comportamento em `supabase/functions/git-proxy/index.ts` e adicionando migração SQL com `GRANT SELECT ON public.sugestoes_branches TO authenticated`, verificando com `deno test supabase/functions/git-proxy/index_test.ts`
- [x] 3.3 Escrever teste em `supabase/functions/create-pr/index_test.ts` para o caso em que `obterArquivosModificadosBranch` falha com `404 Not Found` e atualizar `supabase/functions/create-pr/index.ts` para retornar mensagem diagnóstica clara indicando que a branch não foi encontrada no GitHub, verificando com `deno test supabase/functions/create-pr/index_test.ts`

## 4. Validação Integrada e Recuperação da Publicação Local

- [x] 4.1 Executar a suíte completa de testes afetados e checagens estáticas no `aresta_db` (`uv run ruff check` e `uv run pytest editor/core/sync_test.py editor/core/worker_test.py editor/core/servico_submissao_test.py`) e no `aresta_backend` (`deno test`)
- [x] 4.2 Limpar o remote legado `upstream` no repositório local de dados (`%APPDATA%\Editor Aresta\aresta_db`), posicionar `main` em `origin/main` e preservar/reaplicar os 13 arquivos do commit `83a90bb0` do croqui `br_mg_lagoa_santa_gruta_da_lapinha` sobre a base atualizada
