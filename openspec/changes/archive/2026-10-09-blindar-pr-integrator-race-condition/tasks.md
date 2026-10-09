# Tasks

## 1. Testes Automatizados de Proteção Contra Race Condition

- [x] 1.1 Expandir `tests/workflow_pr_integrator_dco_test.py` com testes unitários cobrindo a existência da etapa prévia de validação global de checks com fail-fast e a inclusão da pasta `database/` no commit de deploy, e confirmar falha inicial (Red)

## 2. Atualização do Workflow do Integrador de PRs

- [x] 2.1 Atualizar `.github/workflows/pr-integrator.yml` inserindo o step `Aguardar e Validar Checagens do Pull Request` logo após a obtenção das informações do PR, com polling e fail-fast para todos os checks ativos
- [x] 2.2 Atualizar o step `Commitar e Enviar Alterações` em `.github/workflows/pr-integrator.yml` para incluir `database/` junto com `generated/` no staging (`git add generated/ database/`)
- [x] 2.3 Executar `uv run python -m unittest tests/workflow_pr_integrator_dco_test.py` e verificar aprovação de todos os testes (Green)

## 3. Validação Geral e Conformidade

- [x] 3.1 Executar a validação de cabeçalhos e licenças (`uv run python -c "from scripts.validador_cabecalhos import validar_todos_cabecalhos_e_licencas; assert not validar_todos_cabecalhos_e_licencas()"`) garantindo conformidade com SPDX MPL-2.0 e Copyright
