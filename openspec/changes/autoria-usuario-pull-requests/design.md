## Context

O Aresta Editor permite que colaboradores editem e criem croquis submetendo propostas de mudança. O fluxo de submissão utiliza o `git-proxy` para enviar as alterações via Git Smart HTTP para a branch `edicao-<id>-<uuid8>` no repositório `aresta-climb/aresta_db`, e em seguida invoca a Edge Function `create-pr` para abrir a Pull Request no GitHub.

Atualmente, a Edge Function `create-pr` utiliza as credenciais do GitHub App (`editor-aresta[bot]`) para executar `octokit.rest.pulls.create`. O Aresta Editor já suporta login via OAuth do GitHub e armazena o `provider_token` na `SessaoUsuario`. Este documento especifica o mecanismo para usar o token do usuário na abertura do PR, garantindo autoria pessoal (`@usuario via editor-aresta[bot]`), mantendo o bot como fallback transparente.

## Goals / Non-Goals

**Goals:**
- Permitir que Pull Requests abertas por usuários autenticados com o GitHub tenham o usuário como autor principal (`@usuario opened this pull request via editor-aresta[bot]`).
- Atualizar o escopo OAuth do GitHub no cliente desktop para incluir `public_repo`.
- Garantir fallback robusto para a credencial do bot GitHub App caso o token do usuário seja inválido, expirado ou caso o login tenha ocorrido via e-mail.
- Manter compatibilidade com a idempotência existente de atualização de PRs abertas.

**Non-Goals:**
- Alterar o protocolo de push Git (o push continua sendo intermediado pelo `git-proxy` com JWT).
- Exigir conta no GitHub para colaboradores logados via e-mail.
- Gerenciar forks pessoais no GitHub dos colaboradores (o fluxo continua utilizando branches `edicao-*` no repositório principal).

## Decisions

### 1. Escopo OAuth no Cliente Desktop
- **Decisão:** Incluir o escopo `public_repo` na URL gerada pela `TelaDeAbertura`: `scopes=read:user,user:email,public_repo`.
- **Alternativas consideradas:**
  - *Usar `repo` completo:* Rejeitado por solicitar permissões excessivas para repositórios privados do usuário.
  - *Solicitar token PAT manual nas configurações:* Rejeitado por introduzir fricção desnecessária quando o login OAuth já fornece o token.

### 2. Transporte do Token do Usuário para `create-pr`
- **Decisão:** Passar `token_usuario_github` (com compatibilidade aceitando também `github_user_token`) no corpo JSON da requisição POST para a Edge Function `create-pr` (autenticada pelo JWT do Supabase).
- **Alternativas consideradas:**
  - *Enviar via Header HTTP `X-GitHub-User-Token`:* Válido, mas o corpo JSON já agrupa os parâmetros da solicitação (`branch`, `title`, `description`) de forma uniforme.

### 3. Autoria e Resiliência na Edge Function `create-pr`
- **Decisão:** Em `create-pr`, se `token_usuario_github` for informado, tentar abrir a PR com `new Octokit({ auth: token_usuario_github })`. Se o token for inválido, faltar escopo ou houver falha de autenticação (401/403), registrar log de aviso e executar fallback para `obterInstanciaOctokit()` (Bot do GitHub App).
- **Alternativas consideradas:**
  - *Falhar a submissão se o token do usuário falhar:* Rejeitado, pois prejudicaria a experiência do colaborador; o envio do croqui deve ser priorizado.

### 4. Estratégia de Testes Conforme PRINCIPIOS.md
- **Testes de Integração em Primeiro Lugar (Princípio V):** Testar a fronteira HTTP e o contrato entre o cliente Python (`editor/core/integracao_submissao_proxy_test.py`) e a Edge Function (`integracao_create_pr_test.ts`), simulando cenários com e sem token de usuário.
- **TDD e Cobertura de 100% (Princípios III e IV):** Implementação estritamente orientada por testes nos módulos `servico_submissao.py`, `tela_de_abertura.py`, `cliente_github_bot.ts` e `create-pr/index.ts`.

## Risks / Trade-offs

- **[Risco] Usuário revoga acesso ou token expira:**  
  → *Mitigação:* A Edge Function `create-pr` captura o erro e realiza fallback transparente para o Bot do GitHub App.
- **[Risco] Usuários com login antigo sem o novo escopo `public_repo`:**  
  → *Mitigação:* Como o fallback para o bot permanece ativo, usuários antigos continuam conseguindo submeter normalmente até efetuarem novo login.
