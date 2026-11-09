# Design

## Context

Consulte `proposal.md` para a motivação completa. Atualmente:
1. Em `aresta_api`, o arquivo `src/proto_validacao_test.py` já concentra os testes comportamentais dos schemas `.proto` (incluindo `test_contratos_beta_midia_limpa_e_arquivo_curadoria_betas`), mas o arquivo legado `src/beta_proto_test.py` permaneceu no repositório tentando instanciar mensagens excluídas (`EscaladaAlvoBusca`, `ViasExtraidasCroqui`, `CandidatosBetaPorEscalada`, `BetasPendentes`) e acessar `midia.snippets` em `Escalada.betas`, causando falha no workflow `generate_protobuf.yml`.
2. Em `aresta_backend/cloudflare/alertas`, `ClienteGithubAppHttp.criarIssueEmergencia` executa sempre `POST /repos/{owner}/{repo}/issues`. Quando um workflow falha em commits seguidos na `main`, são criadas múltiplas Issues com o mesmo título (`🐛 [FALHA DE CI/CD] <workflow> (<branch>)`). Além disso, `obterStepsFalhosWorkflowRun` só é invocado para workflows `pr-*.yml` do `aresta_db`, omitindo quais etapas falharam nos workflows de produção (`main`).

## Goals / Non-Goals

**Goals:**
- Restaurar 100% de aprovação na suíte `uv run pytest` do `aresta_api` consolidando os testes de `Escalada.betas` e `FonteMidia.Enum` em `src/proto_validacao_test.py` e removendo `src/beta_proto_test.py`.
- Evitar a abertura de Issues duplicadas no GitHub pelo `aresta-alertas-worker` quando já houver uma Issue aberta com o mesmo título no mesmo repositório, registrando um comentário com todos os detalhes da nova ocorrência na Issue existente.
- Exibir `Etapa(s) com Erro` em todas as falhas de `workflow_run` (incluindo `main`/`master`/tags e `deploy.yml`), tanto nos alertas enviados ao Discord/`ntfy`/WAHA quanto no corpo da Issue/comentário no GitHub.

**Non-Goals:**
- Fechar automaticamente Issues de CI/CD quando uma execução posterior do workflow tiver sucesso (`conclusion === "success"`): o fechamento permanece deliberadamente manual para exigir análise humana sobre falhas intermitentes (*flaky*) vs. pontuais.

## Decisions

### 1. Consolidação em `src/proto_validacao_test.py` e remoção de `src/beta_proto_test.py`
- **Decisão**: Incorporar a validação comportamental de serialização *round-trip* de `Escalada.betas` e do encapsulamento `FonteMidia.Enum` (`INDEFINIDO = 0`) em `src/proto_validacao_test.py` e excluir `src/beta_proto_test.py`.
- **Racional**: Em `aresta_api/src/`, não existe um módulo `beta_proto.py`; todas as invariantes e contratos de mensagens Protobuf residem em `src/proto_validacao_test.py`. Isso elimina código legado duplicado e *change-detector tests* baseados em `hasattr` estáticos (Princípios III, VI e VII do `AGENTS.md`).

### 2. Consulta de Issues abertas via `GET /repos/{owner}/{repo}/issues?state=open&per_page=100`
- **Decisão**: Em `ClienteGithubAppHttp.criarIssueEmergencia`, antes de executar `POST /repos/{owner}/{repo}/issues`, consultar `GET /repos/{owner}/{repo}/issues?state=open&per_page=100` e procurar um item onde `!item.pull_request && item.title === opcoes.titulo`. Se encontrado, executar `POST /repos/{owner}/{repo}/issues/{number}/comments` com `### 🔄 Nova Ocorrência Detectada\n\n${opcoes.corpo}` e retornar `{ sucesso: true, statusHttp: resComment.status, numeroIssue: existente.number, urlIssue: existente.html_url, comentarioAdicionado: true }`.
- **Alternativas consideradas**:
  - *GitHub Search API (`GET /search/issues`)*: Rejeitada porque possui indexação assíncrona (consistência eventual) e rate limit restrito (30 req/min). Se dois commits falharem em sequência rápida, a primeira Issue pode ainda não estar indexada na busca. O endpoint de listagem do repositório possui consistência imediata.

### 3. Consulta de etapas falhas (`obterStepsFalhosWorkflowRun`) para todos os `workflow_run` que geram alerta
- **Decisão**: Em `classificarWebhookGithub`, quando `eventoGithub === "workflow_run"` falhar e for elegível a alerta (seja `deploy.yml`, `pr-*.yml` ou branch de produção/release `main`/`master`/`v*`), consultar `obterStepsFalhosWorkflowRun` e incluir `• *Etapa(s) com Erro:* ${resumoSteps}` na notificação e `- **Etapa(s) com Erro:** ${resumoSteps}` no corpo da Issue/comentário.
- **Racional**: Permite identificar imediatamente na Issue e em cada comentário de nova ocorrência se uma falha subsequente no mesmo workflow ocorreu na mesma etapa ou em uma etapa distinta (ex: `Run build.py` vs. `Run validation and parity tests`).

## Risks / Trade-offs

- **[Paginação acima de 100 Issues abertas no mesmo repositório]** → Os repositórios da organização `aresta-climb` mantêm poucas Issues abertas simultaneamente; `per_page=100` (que retorna as mais recentes primeiro por padrão) cobre com folga todas as Issues ativas em uma única requisição rápida.
- **[Falha transitória na listagem de Issues abertas]** → Se o `GET .../issues?state=open` retornar erro HTTP (ex: 503 da API do GitHub), `criarIssueEmergencia` falha de forma explícita e aciona o mecanismo existente de fallback na fila de retentativas do Cloudflare KV (`FILA_RETENTATIVAS_ALERTAS`).
