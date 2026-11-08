# Design

## Context

Veja `proposal.md` para a motivação completa e a cadeia das 4 falhas diagnosticadas no incidente `ARESTA-BACKEND-1` (`aresta_backend#5`).

Atualmente:
1. No Editor (`editor/core/sync.py`), `GerenciadorSincronizacao` mantém dois remotes (`origin` e `upstream`) apontando para `https://github.com/aresta-climb/aresta_db.git`. O método `fazer_fetch` deduplica remotes por URL, atualizando apenas `origin/main` e deixando `upstream/main` congelado, enquanto `fazer_checkout_main_upstream` e `ServicoSubmissao._obter_commit_base` priorizam `upstream/main`.
2. Em `editor/core/servico_submissao.py`, `CallbacksProxy` (`pygit2.RemoteCallbacks`) não implementa `push_update_reference(refname, message)`. Na `libgit2`, recusas de referência no protocolo Git Smart HTTP (`HTTP 200 OK` com `ng refs/heads/...` dentro do stream `side-band-64k`) não disparam exceção em `remote.push()`; elas são reportadas apenas via `push_update_reference`.
3. No `aresta_backend` (`supabase/functions/git-proxy/index.ts`), `executarFluxoGitProxy` insere a nova branch na tabela `sugestoes_branches` antes de executar o `POST /git-receive-pack` no GitHub e retorna `respostaGithub.body` sem inspecionar o `report-status` do protocolo `pkt-line`. Se o GitHub rejeitar a criação da ref, o erro passa despercebido no `git-proxy`, o registro fica órfão em `sugestoes_branches` e a falha só explode em `create-pr` quando `compareCommits` retorna `404 Not Found`.

## Goals / Non-Goals

**Goals:**
- Eliminar completamente o remote `upstream` no Editor, tornando `origin` (`refs/remotes/origin/main`) a única fonte de verdade remota e limpando automaticamente remotes `upstream` legados em instalações existentes.
- Garantir que `fazer_push_proxy` falhe imediatamente (lançando `ErroSubmissao` e reportando ao Sentry) sempre que `push_update_reference` receber mensagem de erro não nula do servidor Git.
- Garantir que `git-proxy` inspecione a resposta `pkt-line` (`report-status` direto ou multiplexado em `side-band-64k`) do `git-receive-pack`, reporte recusas (`unpack` != `ok` ou `ng refs/heads/...`) ao Sentry e não deixe registros órfãos em `sugestoes_branches`.
- Retornar diagnóstico claro em `create-pr` caso a branch não exista no GitHub (`404 Not Found` no `compareCommits`).
- Refatorar `editor/core/sync_test.py` para testar configuração de remotes, `fetch` e `checkout` contra repositórios `pygit2` reais em `tmp_path` (Princípios III, V e VII do `AGENTS.md`).

**Non-Goals:**
- Alterar o formato das branches de sugestão (`edicao-<id_croqui>-<uuid8>`) ou o protocolo Git Smart HTTP v1/v2 utilizado entre `pygit2` e `git-proxy`.

## Decisions

### 1. Remoção definitiva do remote `upstream` em vez de sincronização dupla
- **Decisão**: Remover a criação/atualização do remote `upstream` em `configurar_remotes()` e passar a deletar qualquer remote `upstream` existente (assim como já é feito para `proxy`).
- **Racional**: O Aresta Editor não utiliza mais forks na conta do usuário; todo push passa pelo remote efêmero `proxy` (`git-proxy`). Manter dois remotes apontando para o mesmo repositório oficial cria estado duplicado desnecessário. Ao deletar o remote `upstream` em `configurar_remotes()`, a `libgit2` remove automaticamente a referência `refs/remotes/upstream/main` congelada nos repositórios locais existentes dos usuários.
- **Compatibilidade de Nomenclatura**: Em `GerenciadorSincronizacao`, o método `fazer_checkout_main_upstream()` será mantido (ou atualizado internamente para buscar exclusivamente `origin/main`) e `ServicoSubmissao._obter_commit_base()` buscará `refs/remotes/origin/main`, `refs/remotes/origin/master`, `refs/heads/main`, `refs/heads/master`.

### 2. Captura de rejeições de referência via `push_update_reference` em `CallbacksProxy`
- **Decisão**: Em `ServicoSubmissao._obter_callbacks_push`, adicionar o atributo `self.erros_referencia: dict[str, str] = {}` e implementar:
  ```python
  def push_update_reference(self, refname: str, message: str | None) -> None:
      if message is not None:
          self.erros_referencia[refname] = message
  ```
  Logo após `remote.push([f"refs/heads/{nome_branch}"], callbacks=callbacks)`, se `callbacks.erros_referencia` não estiver vazio, lançar `pygit2.GitError` (ou `ErroSubmissao` capturada e enviada ao Sentry na etapa `push_proxy`) contendo os detalhes das referências recusadas.
- **Racional**: É o único mecanismo suportado pela `libgit2` / `pygit2` para detectar falhas de `report-status` (`ng refs/heads/...`) quando o servidor HTTP responde `200 OK`.

### 3. Inspeção do `report-status` (`pkt-line` / `side-band-64k`) e registro pós-push no `git-proxy`
- **Decisão**:
  1. Em `supabase/functions/compartilhado/analisador_pkt_line.ts`, adicionar uma função pura `extrairErrosResultadoReceivePack(buffer: Uint8Array): string[]` que decodifica os pacotes `pkt-line` da resposta do `git-receive-pack` (suportando tanto pacotes diretos quanto pacotes encapsulados no canal `1` do `side-band-64k` `\x01`) e identifica linhas `unpack <erro>` (diferente de `unpack ok`) ou `ng <ref> <motivo>`.
  2. Em `supabase/functions/git-proxy/index.ts`, ler os bytes da resposta do `POST /git-receive-pack` (`new Uint8Array(await respostaGithub.arrayBuffer())`), verificar status HTTP e `extrairErrosResultadoReceivePack(bytesResposta)`:
     - Se houver erro HTTP ou erro no `report-status`, relatar ao Sentry com `etapa: "git_receive_pack"` e **não registrar** a branch em `sugestoes_branches` (fazendo o registro em `sugestoes_branches` apenas após confirmação de que o push ao GitHub teve sucesso, após validar previamente que a branch não existia no GitHub nem no banco!).
- **Alternativa considerada**: Registrar antes no banco e deletar em caso de falha. Fazer a validação de conflito (`jaExisteNoGithub || jaExisteNoBanco`) antes do push e inserir em `sugestoes_branches` somente após o `git-receive-pack` retornar sucesso evita completamente a necessidade de `DELETE` compensatório e impede registros órfãos.

## Risks / Trade-offs

- **[Risco] Testes existentes que criam apenas `refs/remotes/upstream/main` em fixtures** → **Mitigação**: Atualizar as fixtures de teste em `servico_submissao_test.py`, `integracao_submissao_proxy_test.py` e `sincronizacao_pr_integracao_test.py` para usar `refs/remotes/origin/main`.
- **[Risco] Leitura de `arrayBuffer()` da resposta do `git-receive-pack` no `git-proxy`** → **Mitigação**: Enquanto a requisição de entrada pode ter vários megabytes (packfile), a resposta de saída do `git-receive-pack` tem apenas algumas centenas de bytes (progresso do `unpack` + `report-status` das refs), portanto ler seu `arrayBuffer()` antes de retornar a `Response` tem custo de memória desprezível (< 4 KB).

## Migration Plan

1. Implementar e testar as alterações no `aresta_db` (`editor/core/sync.py`, `editor/core/servico_submissao.py`, `editor/core/worker.py` e respectivos `_test.py`).
2. Implementar e testar as alterações no `aresta_backend` (`analisador_pkt_line.ts`, `git-proxy/index.ts`, `create-pr/index.ts` e migração SQL) e realizar o deploy das Edge Functions `git-proxy` e `create-pr`.
3. No repositório local de dados do usuário (`%APPDATA%\Editor Aresta\aresta_db`), remover o remote legado `upstream`, posicionar `main` em `origin/main` e recriar/enviar a branch da Gruta da Lapinha com os 13 arquivos do commit `83a90bb0`.
