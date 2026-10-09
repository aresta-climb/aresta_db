# Design

## Context

Atualmente, o fluxo de automação de Pull Requests utiliza o GitHub App oficial Probot DCO para garantir que contribuições venham acompanhadas de `Signed-off-by`. Quando uma revisão é aprovada, o workflow `.github/workflows/pr-integrator.yml` gera os artefatos de produção em `generated/`, efetua um commit com push e em seguida executa `gh pr merge` utilizando o token do GitHub App (`BOT_APP_ID`).

Por possuir privilégios administrativos de bypass em branch protection rules, o token do bot efetua o merge imediatamente sem verificar se os status checks do PR (especificamente o DCO) foram concluídos com sucesso. Além disso, a ausência de `.github/dco.yml` faz com que o Probot DCO exija assinatura manual mesmo para membros da organização que realizam alterações na interface web do GitHub.

## Goals / Non-Goals

**Goals:**
- Configurar o Probot DCO via `.github/dco.yml` para dispensar exigência de `Signed-off-by` em commits verificados de membros da organização (`require.members: false`).
- Adicionar uma etapa explícita de verificação do status check `DCO` no workflow `.github/workflows/pr-integrator.yml` antes da chamada de merge.
- Implementar polling defensivo para aguardar a conclusão da checagem do DCO após o `git push` executado pelo bot integrador.
- Abortar a execução do integrador (código de saída 1) e bloquear o merge caso o check do DCO falhe ou não passe com sucesso.

**Non-Goals:**
- Não reimplementar a validação do DCO em Python nem criar daemons/serviços adicionais, mantendo a arquitetura simples e sem código desnecessário.
- Não alterar as regras de compilação ou validação dos outros workflows (`pr-code-validator.yml`, `pr-db-validator.yml`).
- Não remover nem alterar a obrigatoriedade de `Signed-off-by` para contribuidores externos.

## Decisions

### Decisão 1: Manter o Probot DCO com configuração `.github/dco.yml`
- **Escolha**: Criar `.github/dco.yml` com:
  ```yaml
  require:
    members: false
  ```
- **Racional**: O Probot DCO verifica nativamente se o autor pertence à organização do GitHub e se o commit é verificado criptograficamente (`commit.verification.verified`). Commits realizados diretamente pela UI web do GitHub são automaticamente assinados pela chave GPG do GitHub (`web-flow`), satisfazendo a condição sem necessidade de tags de texto. Além disso, as submissões enviadas pelo Aresta Editor já incluem automaticamente `Signed-off-by: Nome <email>`, sendo aceitas sem qualquer modificação.
- **Alternativas consideradas**:
  - *Criar validador customizado em Python*: Rejeitado por violar o princípio de Simplicidade e Anti-Abstração (complexidade desnecessária), uma vez que a configuração declarativa padrão do Probot DCO atende integralmente ao caso de uso.

### Decisão 2: Inspecionar o status check `DCO` via `gh pr checks` no `pr-integrator.yml`
- **Escolha**: Utilizar o comando oficial do GitHub CLI:
  ```bash
  gh pr checks "$PR_ID" --repo ${{ github.repository }} --json name,bucket,state
  ```
  filtrando a entrada onde `.name == "DCO"`.
- **Racional**: A CLI `gh` já vem pré-instalada nos runners `ubuntu-latest` do GitHub Actions e já está autenticada no workflow com o token do app. A propriedade `bucket` categoriza o status de forma limpa em `pass`, `fail`, `pending`, `skipping` ou `cancel`.
- **Alternativas consideradas**:
  - *Consultar via API REST de check-runs*: Mais verboso e suscetível a paginação de SHAs comparado à abstração robusta do `gh pr checks`.

### Decisão 3: Aguardar reavaliação do DCO após o push de deploy
- **Escolha**: Como o passo anterior executa `git push` com as compilações de `generated/`, o GitHub recebe um novo commit na branch do PR (`pull_request.synchronize`). O `pr-integrator` implementará um loop de até 15 tentativas (intervalo de 3 segundos, ~45s no total):
  1. Consulta o bucket do check `DCO`.
  2. Se `pass`, prossegue imediatamente para a etapa de merge.
  3. Se `fail` ou `cancel`, emite erro e finaliza com `exit 1`.
  4. Se pendente ou não encontrado ainda, aguarda e tenta novamente.
  5. Se esgotar as tentativas sem aprovação, falha com `exit 1`.
- **Racional**: Evita condições de corrida onde o bot tenta mergiar antes que o Probot DCO processe o webhook do novo commit gerado pelo próprio deploy.

## Risks / Trade-offs

- **[Risco] Mantenedor efetua commit localmente via terminal sem flag `-s` e sem chave GPG/SSH configurada**:
  - *Mitigação*: O Probot DCO bloqueará o PR informando `"Commit by organization member is not verified."`. O mantenedor poderá simplesmente rodar `git commit --amend -s` e efetuar push forçado, ou configurar assinatura SSH/GPG no Git local (`git config commit.gpgsign true`).
- **[Risco] Lentidão temporária do Probot DCO (GitHub App externo)**:
  - *Mitigação*: O loop de polling com até 45s de tolerância cobre com folga o tempo de resposta habitual do bot (1-5s). Caso ocorra indisponibilidade no Probot, o integrador falha de forma segura (fail-closed), nunca mergiando código não verificado.
