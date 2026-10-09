# Design

## Context

O workflow `.github/workflows/pr-integrator.yml` é acionado pelo evento de aprovação de Pull Request (`pull_request_review: approved` ou `/approve`). Quando disparado, o integrador executa utilizando o token do GitHub App (`BOT_APP_ID`), que possui privilégios de bypass sobre as regras de branch protection do repositório.

Anteriormente, o integrador executava o deploy gerado, commitava na branch do PR e inspecionava exclusivamente o check `DCO`. Caso outros validadores (como `pr-db-validator` ou `pr-code-validator`) ainda estivessem em execução em paralelo ou já tivessem falhado, a chamada `gh pr merge` realizava o merge imediato no `main` sem que o GitHub bloqueasse a ação, resultando em race condition e integração de PRs com falhas. Além disso, o commit do bot incluía apenas `git add generated/`, ignorando alterações legítimas aplicadas pelo compilador aos arquivos da pasta `database/`.

## Goals / Non-Goals

**Goals:**
- Validar todas as checagens ativas do PR antes de iniciar o deploy, aguardando que todas concluam com sucesso (`pass` ou `skipping`).
- Abortar a execução do integrador imediatamente em caso de falha de qualquer check (`fail` ou `cancel`) em modo fail-fast.
- Atualizar a rotina de commit do integrador para incluir tanto `generated/` quanto `database/` (`git add generated/ database/`).
- Manter a verificação do check `DCO` após o commit do bot para assegurar que a nova revisão também seja aceita antes do merge.

**Non-Goals:**
- Não alterar as regras de validação nem os critérios internos de aprovação dos validadores (`pr-db-validator.yml` e `pr-code-validator.yml`).
- Não remover os privilégios de bypass do GitHub App Token, que continuam necessários para o push e merge direto pelo bot.

## Decisions

### Decisão 1: Verificação antecipada de todos os checks ativos com Fail-Fast
- **Escolha**: Inserir um step obrigatório logo no início do job `integrate` (após obter as informações do PR) que executa polling dinâmico sobre `gh pr checks "$PR_ID"`:
  ```bash
  CHECKS_JSON=$(gh pr checks "$PR_ID" --repo ${{ github.repository }} --json name,bucket,state 2>/dev/null || echo "[]")
  ```
- **Racional**:
  1. Se qualquer check apresentar `bucket == "fail"` ou `bucket == "cancel"`, o step emite log identificando os checks que falharam e encerra imediatamente com `exit 1` (fail-fast), sem realizar checkout, deploy nem merge.
  2. Se houver checks com `bucket == "pending"`, o loop aguarda em intervalos de 10 segundos por até 12 minutos (72 iterações), cobrindo a duração máxima de `pr-code-validator` e `pr-db-validator`.
  3. Só avança para as etapas de deploy se todos os checks ativos tiverem `bucket` em `pass` ou `skipping`.
  4. Por ser dinâmico, protege automaticamente novos workflows e checagens adicionados ao repositório no futuro.

### Decisão 2: Staging abrangente de `generated/` e `database/`
- **Escolha**: Modificar o comando no passo de commit para:
  ```bash
  git add generated/ database/
  ```
- **Racional**: O script `deploy_generated.py` pode atualizar identificadores estáveis, metadados de migração e sanitizações nos arquivos fonte de `database/`. Commitar ambas as pastas garante atomicidade e evita que modificações fiquem desanexadas ou sujas na árvore de trabalho.

## Risks / Trade-offs

- **[Risco] PR recém-aberto sem checks registrados no primeiro segundo da aprovação**:
  - *Mitigação*: O loop de polling inicial verifica se o total de checks é zero e aguarda alguns segundos para dar tempo de o GitHub Actions enfileirar os jobs do PR antes de avaliar a conclusão.
- **[Risco] Atrasos na execução de testes de código lentos**:
  - *Mitigação*: O limite de até 12 minutos comporta a suíte de testes unitários do editor com folga. Se houver falha, ela é detectada imediatamente pelo critério fail-fast sem aguardar o tempo limite.
