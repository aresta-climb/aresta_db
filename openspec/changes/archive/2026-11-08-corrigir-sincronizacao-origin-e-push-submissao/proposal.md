# Proposal

## Why

Durante a publicação de croquis no Editor Aresta (observado no croqui `br_mg_lagoa_santa_gruta_da_lapinha` e registrado no Sentry em `ARESTA-BACKEND-1` / `aresta_backend#5`), o fluxo de submissão falhava na abertura da Pull Request com `Erro 400: Falha ao inspecionar branch no GitHub: Not Found`. A investigação revelou uma cadeia de quatro problemas: (1) a manutenção redundante dos remotes `origin` e `upstream` combinada à deduplicação de URLs em `fazer_fetch` deixava `refs/remotes/upstream/main` congelado no passado enquanto o checkout e a criação de branches de sugestão priorizavam `upstream/main`; (2) o `CallbacksProxy` do `pygit2` não implementava `push_update_reference`, engolindo silenciosamente recusas de atualização de referência (`ng refs/heads/...`) retornadas com HTTP 200 pelo protocolo Git Smart HTTP; (3) o `git-proxy` registrava a nova branch na tabela `sugestoes_branches` antes da confirmação do `git-receive-pack` e não inspecionava falhas de ref no protocolo `pkt-line`; e (4) o `create-pr` repassava a mensagem crua `Not Found` do `compareCommits` sem explicitar que a branch não existia no GitHub.

## What Changes

- **BREAKING (Interno — Sincronização Git)**: Remoção definitiva do remote `upstream` no `GerenciadorSincronizacao` (`editor/core/sync.py`), unificando toda a sincronização, checkout da branch principal e obtenção de commit base exclusivamente no remote `origin` (`refs/remotes/origin/main`). Repositórios locais existentes que possuam o remote legado `upstream` terão esse remote e suas referências defasadas removidos automaticamente em `configurar_remotes()`.
- **Detecção de falha de atualização de referência no Push (`editor/core/servico_submissao.py`)**: Implementação do callback `push_update_reference(refname, message)` em `CallbacksProxy` (`pygit2.RemoteCallbacks`) para capturar qualquer recusa do servidor Git (`message is not None`) durante `fazer_push_proxy`, reportando a falha ao Sentry na etapa `push_proxy` e lançando `ErroSubmissao` imediatamente antes de tentar abrir a Pull Request.
- **Inspeção de resultado e consistência transacional no `git-proxy` (`aresta_backend`)**: Inspeção do resultado `pkt-line` (`report-status` / `side-band-64k`) retornado pelo `git-receive-pack` do GitHub na Edge Function `git-proxy`, reportando falhas de `unpack` ou `ng refs/heads/...` ao Sentry e garantindo que branches cuja criação falhou no GitHub não permaneçam órfãs na tabela `sugestoes_branches`. Adição de `GRANT SELECT ON public.sugestoes_branches TO authenticated` na migração do Supabase.
- **Diagnóstico explícito de branch ausente no `create-pr` (`aresta_backend`)**: Tratamento específico de erro `404 Not Found` em `obterArquivosModificadosBranch` na Edge Function `create-pr`, retornando mensagem clara indicando que a branch da proposta não foi encontrada no repositório remoto do GitHub.
- **Refatoração de testes para fidelidade de produção (`editor/core/sync_test.py`)**: Substituição dos mocks de `pygit2` nos testes de remotes, fetch e checkout por repositórios `pygit2` reais em `tmp_path`, em conformidade com os Princípios III, V e VII do `AGENTS.md`.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability introduzida. -->

### Modified Capabilities
- `editor-sincronizacao-git`: Elimina o conceito de fork e remote `upstream`, unificando a configuração de remotes, o `fetch` e o checkout da branch principal exclusivamente em `origin` (`origin/main`) e limpando remotes `upstream` legados.
- `editor-submissao-sugestoes`: Define `origin/main` como única referência base remota para criação de branches de sugestão e exige a verificação de `push_update_reference` no `pygit2` para interromper e reportar falhas de criação/atualização de referência remota durante o `fazer_push_proxy`.
- `backend-git-proxy`: Exige inspeção do status de atualização de referências do `git-receive-pack` do GitHub, telemetria de recusas `pkt-line` no Sentry e prevenção/limpeza de registros órfãos em `sugestoes_branches` quando o push não efetiva a criação da branch.
- `backend-pr-api`: Especifica mensagem diagnóstica clara quando a branch informada para abertura de Pull Request não é encontrada (`404 Not Found`) no repositório do GitHub.

## Impact

- **Repositório `aresta_db`**:
  - `editor/core/sync.py` e `editor/core/sync_test.py`
  - `editor/core/worker.py` e `editor/core/worker_test.py`
  - `editor/core/servico_submissao.py` e `editor/core/servico_submissao_test.py`
  - `editor/core/integracao_submissao_proxy_test.py` e `editor/core/sincronizacao_pr_integracao_test.py`
- **Repositório `aresta_backend`**:
  - `supabase/functions/git-proxy/index.ts` e `supabase/functions/git-proxy/index_test.ts`
  - `supabase/functions/create-pr/index.ts` e `supabase/functions/create-pr/index_test.ts`
  - `supabase/functions/compartilhado/analisador_pkt_line.ts` e `supabase/functions/compartilhado/analisador_pkt_line_test.ts`
  - `supabase/ functions/compartilhado/cliente_supabase_controle.ts` e `supabase/functions/compartilhado/cliente_supabase_controle_test.ts`
  - `supabase/migrations/` (permissão `GRANT SELECT` para `authenticated` em `sugestoes_branches`)
