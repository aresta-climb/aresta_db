## 1. Testes de Integração e Unidade (TDD First)

- [ ] 1.1 Criar `scripts/test_integracao_gerar_croqui.py` definindo os contratos e os cenários E2E locais (verificar a criação da estrutura de pastas correta e o ZIP ofuscado no disco).
- [ ] 1.2 Criar `scripts/gerar_croqui_experimental_test.py` com cenários exaustivos buscando 100% de cobertura (unit test coverage).
- [ ] 1.3 Criar `serving/pr_validator_test.py` garantindo que o relatório de falhas e sucessos seja gerado corretamente e o exit code respeite as falhas.

## 2. Implementação (Library-First)

- [ ] 2.1 Refatorar `scripts/deploy_generated.py` para suportar a flag `--target` com múltiplos argumentos (`nargs='+'`), validando que a compilação local continua íntegra.
- [ ] 2.2 Implementar a biblioteca `scripts/gerar_croqui_experimental.py` garantindo que ela passe em todos os testes criados, com docstrings claras, completas e em português brasileiro, de forma declarativa e simples (anti-abstração).
- [ ] 2.3 Implementar `serving/pr_validator.py` consumindo as bibliotecas, de forma simples e direta, mantendo 100% de coverage.

## 3. GitHub Actions Workflows

- [ ] 3.1 Configurar o workflow `.github/workflows/pr-validator.yml` trigado em `pull_request` acoplando `tj-actions/changed-files`.
- [ ] 3.2 Configurar o workflow `.github/workflows/pr-integrator.yml` trigado em `pull_request_review`, configurando o App Token, bypass de proteção e automerge.
- [ ] 3.3 Criar stub do workflow `.github/workflows/deploy.yml` para push na `main`.

## 4. Validação End-to-End

- [ ] 4.1 Abrir um PR fictício modificando um detalhe em `database/` para acionar os workflows.
- [ ] 4.2 Verificar a correta execução, aprovação, push com `[skip ci]` e merge autônomo na branch `main`.
