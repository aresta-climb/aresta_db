# Proposal

## Why

A evolução de `beta.proto` (que removeu as mensagens intermediárias legadas e limpou `MidiaBeta` mantendo apenas `url`, `titulo` e `fonte`) deixou para trás o arquivo de teste legado `aresta_api/src/beta_proto_test.py`, quebrando a etapa `Run validation and parity tests` do workflow `Gerar Contratos e Bindings (Protobuf, SQL, OpenAPI)` na branch `main` (Issues `aresta-climb/aresta_api#1` e `#2`). Além disso, a segunda execução falha do mesmo workflow revelou que o `aresta-alertas-worker` (`aresta_backend`) cria uma nova Issue duplicada a cada falha consecutiva de um mesmo workflow/alerta que já possui Issue aberta no GitHub e não informa quais etapas (`steps`) falharam nos workflows de produção (`main`).

## What Changes

- **Consolidação dos testes de contrato de `beta.proto` em `aresta_api`**:
  - Consolidar em `aresta_api/src/proto_validacao_test.py` a validação comportamental de serialização *round-trip* de `Escalada.betas` (contendo `MidiaBeta` limpa com `url`, `titulo` e `fonte`) e do encapsulamento de `FonteMidia.Enum` (`INDEFINIDO = 0`).
  - Remover o arquivo de teste legado órfão `aresta_api/src/beta_proto_test.py` (que testava mensagens removidas como `EscaladaAlvoBusca` e `snippets` em `MidiaBeta` via *change-detector tests* em inglês).
- **Deduplicação de Issues abertas com comentário de nova ocorrência no `aresta-alertas-worker` (`aresta_backend`)**:
  - Atualizar `ClienteGithubAppHttp.criarIssueEmergencia` (e `ClienteGithubAppFake`) para consultar as Issues abertas do repositório destino (`GET /repos/{owner}/{repo}/issues?state=open&per_page=100`) antes de criar uma nova Issue.
  - Se já existir uma Issue aberta (`!pull_request`) com exatamente o mesmo `titulo`, adicionar um comentário (`POST /repos/{owner}/{repo}/issues/{number}/comments`) contendo os detalhes completos da nova ocorrência (`### 🔄 Nova Ocorrência Detectada\n\n` + `corpo`) e retornar o número e a URL da Issue existente (`comentarioAdicionado: true`), enviando normalmente a notificação nos canais (Discord, `ntfy`, WAHA) com o link da Issue existente e mantendo o fechamento manual.
- **Inclusão das etapas falhas (`Etapa(s) com Erro`) nos alertas de `workflow_run` de produção (`main`)**:
  - Consultar `obterStepsFalhosWorkflowRun` também para falhas de workflows na branch `main`/`master`/tags (`🐛 [FALHA DE CI/CD]` e `🚨 [FALHA DE DEPLOY/CI]`), incluindo `- **Etapa(s) com Erro:** <steps>` tanto no texto da notificação quanto no corpo da Issue/comentário no GitHub.

## Capabilities

### New Capabilities
- `roteador-alertas-deduplicacao-issues`: Deduplicação de Issues automáticas abertas pelo `aresta-alertas-worker` (adicionando comentário com os detalhes da nova ocorrência quando já existir Issue aberta de mesmo título no repositório) e enriquecimento de falhas de `workflow_run` na branch de produção com a lista de etapas (`steps`) que falharam.

### Modified Capabilities
- `beta-model`: Atualização da validação de contrato de `beta.proto` e `Escalada.betas` em `aresta_api/src/proto_validacao_test.py` sem testes legados acoplados a estruturas removidas.

## Impact

- **`aresta_api` (`c:\Renato\Devel\aresta-climb\aresta_db\aresta_api`)**:
  - `src/proto_validacao_test.py` (adição da verificação comportamental de serialização de `Escalada.betas` e `FonteMidia.Enum`)
  - `src/beta_proto_test.py` (remoção do arquivo órfão legado)
- **`aresta_backend` (`c:\Renato\Devel\aresta-climb\aresta_backend\cloudflare\alertas`)**:
  - `src/cliente_notificacao_fake.ts` e `test/cliente_notificacao_fake.test.ts`
  - `src/index.ts` e `test/index.test.ts`
