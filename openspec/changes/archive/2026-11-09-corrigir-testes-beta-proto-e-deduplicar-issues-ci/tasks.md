# Tasks

## 1. Consolidação dos Testes de Contrato de `beta.proto` no `aresta_api`

- [x] 1.1 Adicionar em `aresta_api/src/proto_validacao_test.py` a validação comportamental de serialização *round-trip* de `Escalada.betas` (com `MidiaBeta` limpa contendo `url`, `titulo` e `fonte`) e do encapsulamento `FonteMidia.Enum` (`INDEFINIDO = 0`), verificando com `uv run pytest src/proto_validacao_test.py`
- [x] 1.2 Remover o arquivo de teste legado órfão `aresta_api/src/beta_proto_test.py` e verificar que toda a suíte `uv run pytest` em `aresta_api` passa sem erros

## 2. Deduplicação de Issues e Etapas com Erro no `aresta-alertas-worker` (`aresta_backend`)

- [x] 2.1 Atualizar `ClienteGithubAppFake` e `ResultadoCriarIssueGithub` em `aresta_backend/cloudflare/alertas/src/cliente_notificacao_fake.ts` (e seu teste espelhado `test/cliente_notificacao_fake.test.ts` via TDD Red-Green-Refactor) para deduplicar Issues abertas de mesmo `repositorio` e `titulo`, registrando comentários em `comentariosAdicionados` e retornando `comentarioAdicionado: true`
- [x] 2.2 Atualizar `ClienteGithubAppHttp.criarIssueEmergencia` em `aresta_backend/cloudflare/alertas/src/index.ts` (e `test/index.test.ts` via TDD Red-Green-Refactor) para consultar `GET /repos/{owner}/{repo}/issues?state=open&per_page=100`, comentar `### 🔄 Nova Ocorrência Detectada\n\n<corpo>` via `POST .../issues/{number}/comments` quando a Issue já estiver aberta e manter o envio da notificação (Discord, `ntfy`, WAHA) apontando para a Issue existente
- [x] 2.3 Atualizar `classificarWebhookGithub` em `aresta_backend/cloudflare/alertas/src/index.ts` (e `test/index.test.ts`) para consultar `obterStepsFalhosWorkflowRun` e incluir `Etapa(s) com Erro` também nas falhas de `workflow_run` da branch de produção/release (`🐛 [FALHA DE CI/CD]`) e de deploy (`🚨 [FALHA DE DEPLOY/CI]`), verificando que toda a suíte de testes do worker passa com 100% de cobertura comportamental
