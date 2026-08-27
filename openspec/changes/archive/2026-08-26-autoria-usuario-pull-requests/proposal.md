## Why

Atualmente, todas as Pull Requests de sugestão/edição de croquis são abertas utilizando a credencial do bot GitHub App (`editor-aresta[bot]`). Embora a autoria do commit e a assinatura DCO reflitam o usuário real, no topo do Pull Request no GitHub quem figura como autor é o bot.

Quando o usuário se autentica através do GitHub no Aresta Editor, já possuímos o `provider_token` (token de acesso OAuth do usuário). Permitir que o PR seja aberto com esse token confere autoria direta ao usuário (`@usuario opened this pull request via editor-aresta[bot]`), permitindo que ele receba notificações nativas do GitHub, participe das discussões e construa histórico público de contribuição na plataforma. Para usuários logados via e-mail ou sem token GitHub, o bot continua operando como fallback transparente.

## What Changes

- **Escopo OAuth no Aresta Editor:** Inclusão do escopo `public_repo` no fluxo de autorização OAuth do GitHub na `TelaDeAbertura`, permitindo abertura de PRs em repositórios públicos em nome do usuário autenticado.
- **Transmissão do Token OAuth no Cliente (Library-First):** Atualização da biblioteca `ServicoSubmissao` (`solicitar_abertura_pr`) para enviar o `token_usuario_github` (se presente em `SessaoUsuario`) na chamada à Edge Function `create-pr`.
- **Autoria Dinâmica na Edge Function `create-pr` (`aresta_backend`):** 
  - Aceita `token_usuario_github` opcional no corpo da requisição JSON.
  - Se fornecido, instancia o `Octokit` com o token do usuário para criar a Pull Request (resultando na autoria `@usuario via editor-aresta[bot]`).
  - Se ausente ou se a chamada falhar (token revogado/expirado), realiza fallback seguro e automático para o GitHub App Bot (`editor-aresta[bot]`).
- **Conformidade Estrita com PRINCIPIOS.md:** Desenvolvimento guiado por TDD (Red-Green-Refactor), testes de integração em primeiro lugar nas fronteiras de API, 100% de cobertura de testes unitários nos módulos afetados e código integralmente em português.

## Capabilities

### New Capabilities

*(Nenhuma nova capacidade isolada necessária)*

### Modified Capabilities

- `editor-submissao-sugestoes`: Atualização dos requisitos de submissão e abertura de Pull Request para suportar autoria direta do usuário via token OAuth GitHub e fallback automático para o bot.

## Impact

- **`aresta_db` (Desktop):**
  - `editor/views/tela_de_abertura.py`: Atualização do parâmetro `scopes` na URL de autorização OAuth.
  - `editor/core/servico_submissao.py`: Inclusão do parâmetro `token_github` em `solicitar_abertura_pr` e `submeter_sugestao`.
  - `editor/core/worker.py`: Repasse da sessão para obtenção do token.
  - Testes unitários e de integração correspondentes (`servico_submissao_test.py`, `integracao_submissao_proxy_test.py`, `tela_de_abertura_test.py`).
- **`aresta_backend` (Supabase Functions):**
  - `supabase/functions/create-pr/index.ts`: Extração de `token_usuario_github` (com compatibilidade a `github_user_token`) e repasse para o cliente Octokit.
  - `supabase/functions/compartilhado/cliente_github_bot.ts`: Suporte a token de usuário com fallback para o token do bot.
  - Testes de integração e unitários em Deno (`create-pr/index_test.ts`, `cliente_github_bot_test.ts`, `integracao_create_pr_test.ts`).
