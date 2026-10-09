# Proposal

## Why

Atualmente, o workflow do integrador automático (`pr-integrator.yml`) executa em paralelo quando uma aprovação é emitida, mas não aguarda a conclusão das checagens ativas de validação do Pull Request (como `pr-db-validator` ou `pr-code-validator`). Como o integrador utilizava credenciais do GitHub App com permissão de bypass de branch protection e verificava apenas o status do DCO, ocorreu uma race condition na qual o integrador realizou o merge direto de um Pull Request no branch `main` enquanto o validador do banco de dados ainda estava em execução ou já havia falhado.

Além disso, a rotina de commit do integrador realizava apenas `git add generated/`, deixando de fora possíveis alterações e sanitizações que o script `deploy_generated.py` realiza nos arquivos fonte dentro de `database/`, correndo o risco de deixar o repositório em estado inconsistente.

## What Changes

- **Garantia Prévia de Sucesso de Todas as Checagens (Fail-Fast)**: Inclusão de etapa mandatória no início do workflow `pr-integrator.yml` que consulta dinamicamente todas as checagens ativas do PR (`gh pr checks`). O workflow aguarda até que todas as checagens terminem e aborta imediatamente (`exit 1`) caso qualquer checagem falhe ou seja cancelada, impedindo a geração de deploy e o merge de PRs inválidos.
- **Inclusão de `database/` no Commit de Deploy**: Atualização do passo de commit do integrador para executar `git add generated/ database/`, garantindo que arquivos enriquecidos ou normalizados pela compilação sejam versionados no mesmo commit de deploy.
- **Revalidação Pós-Deploy**: Preservação da checagem do DCO após o commit do bot para garantir que o novo commit com `[skip ci]` seja devidamente reconhecido antes do merge final.

## Capabilities

### New Capabilities
*(Nenhuma nova capacidade necessária)*

### Modified Capabilities
- `ci-cd-workflow-pr`: Atualização do requisito `Bot Integrator on Pull Request Approval` para exigir que TODAS as checagens ativas do Pull Request estejam concluídas e aprovadas antes de gerar o deploy e realizar o merge, abortando imediatamente em caso de falha de qualquer validador, e garantindo a inclusão das pastas `generated/` e `database/` no commit automático.

## Impact

- **`.github/workflows/pr-integrator.yml`**: Novo step inicial de validação global de checks com polling defensivo e fail-fast; alteração do comando de staging para `git add generated/ database/`.
- **`tests/workflow_pr_integrator_dco_test.py`**: Expansão dos testes unitários para validar a presença da verificação de todas as checagens ativas e a inclusão de `database/` no commit.
- **Nenhum impacto de quebra (breaking change)**: O fluxo de aprovação e merge permanece idêntico do ponto de vista do usuário/mantenedor, porém torna-se 100% blindado contra race conditions.
