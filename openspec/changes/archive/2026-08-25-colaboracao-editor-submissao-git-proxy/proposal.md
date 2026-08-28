## Why

Usuários da comunidade que editam croquis no Aresta Editor não possuem permissão de escrita direta no repositório oficial (`aresta-climb/aresta_db`) nem suporte para criação automática de forks em suas contas pessoais do GitHub. Com o Supabase Git Proxy (Sub-projeto 1) e a autenticação OTP/OAuth (Sub-projeto 2) já operacionais, é necessário implementar no cliente Desktop a engine de submissão que realiza commit local com `pygit2`, push seguro através do Git Proxy e formalização automatizada da Pull Request via Edge Function `create-pr`.

## What Changes

- **Aproveitamento da Base Existente:** Reutilização direta dos algoritmos maduros do editor de sincronização de diretórios (`sync_dir`), staging no índice Git (`index.add_all`), validação de alterações (`write_tree`), criação de commit e branch com `pygit2`, persistência de metadados em `croqui_experimental.yaml` e componentes de diálogo (`PublishDialog`, `DialogoSucessoPR`, `QProgressDialog`).
- **Biblioteca `ServicoSubmissao` (Library-First):** Extração e desacoplamento da lógica central de submissão para uma biblioteca pura e 100% testável, responsável por gerar o nome da branch (`sugestao-<id_croqui>-<uuid8>`), assinar o commit com a `SessaoUsuario`, configurar o push autenticado via JWT para a Edge Function `git-proxy` e disparar a abertura da PR via REST na Edge Function `create-pr`.
- **Remoção de PyGithub do Fluxo de Submissão:** Eliminação completa da dependência de `github.Github` (PyGithub), criação de forks pessoais e tokens com permissão de repositório para o autor. O fluxo passa a ser 100% suportado por `pygit2` + `requests`.
- **Validações Pré-Envio:** Verificação local de compilação sem erros, checagem de modificações reais em relação à `upstream/main` e exibição de resumo de arquivos a serem enviados no diálogo de submissão.
- **Gestão de Sessão no Push:** Renovação silenciosa preventiva do JWT antes do push; em caso de expiração irrecuperável, solicitação de salvamento de alterações e reinício do fluxo de autenticação.
- **Atualização Inteligente de PRs Existentes:** Reutilização automática da mesma branch caso o croqui já possua uma PR aberta pelo autor; limpeza automática do vínculo e criação de nova branch se a PR anterior tiver sido fechada ou aceita (merged).
- **Refatoração de `PublishController` e `TarefaPublicacao`:** Orquestração assíncrona enxuta conectada ao `ServicoSubmissao` e `SessaoUsuario`.

## Capabilities

### New Capabilities
- `editor-submissao-sugestoes`: Gerencia a criação de commits locais assinados com `pygit2`, envio via Git Smart HTTP para o Supabase Git Proxy e criação/atualização de Pull Requests através da Edge Function `create-pr`.

### Modified Capabilities
<!-- Nenhuma especificação existente teve seus requisitos modificados -->

## Impact

- **Código Afetado:**
  - `editor/core/integracao_submissao_proxy_test.py` (teste de integração de fronteira fim-a-fim conforme Princípio V).
  - `editor/core/servico_submissao.py` (novo módulo library-first conforme Princípio II).
  - `editor/core/servico_submissao_test.py` (testes unitários com 100% de cobertura e TDD conforme Princípios III e IV).
  - `editor/core/worker.py` (`TarefaPublicacao`).
  - `editor/core/worker_test.py`.
  - `editor/controllers/publish_controller.py`.
  - `editor/controllers/publish_controller_test.py`.
- **APIs e Serviços Externos:**
  - Supabase Edge Functions: `POST /functions/v1/git-proxy/git-receive-pack` e `POST /functions/v1/create-pr`.
  - Protocolo Git Smart HTTP (v2) sobre HTTPS.
