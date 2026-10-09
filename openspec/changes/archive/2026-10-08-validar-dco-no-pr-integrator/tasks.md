# Tasks

## 1. Configuração do Probot DCO

- [x] 1.1 Criar o arquivo `.github/dco.yml` com `require: members: false` e verificar que o conteúdo YAML é válido
- [x] 1.2 Criar teste unitário em `tests/workflow_pr_integrator_dco_test.py` validando a presença e as diretivas de `.github/dco.yml` e verificar aprovação

## 2. Atualização do Workflow do Integrador de PRs

- [x] 2.1 Adicionar casos de teste em `tests/workflow_pr_integrator_dco_test.py` validando a presença e a lógica do passo de verificação do check `DCO` antes do merge em `.github/workflows/pr-integrator.yml` e confirmar falha inicial (Red)
- [x] 2.2 Atualizar `.github/workflows/pr-integrator.yml` adicionando o step `Aguardar e Verificar Check do DCO` com polling defensivo via `gh pr checks` e aborto em caso de falha
- [x] 2.3 Executar `uv run python -m unittest tests/workflow_pr_integrator_dco_test.py` e verificar aprovação de todos os testes (Green)

## 3. Validação Geral e Conformidade

- [x] 3.1 Executar o validador de cabeçalhos e licenças (`uv run python scripts/validador_cabecalhos.py`) garantindo conformidade com SPDX MPL-2.0 e Copyright
