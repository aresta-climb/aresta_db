## 1. Configuração dos Workflows de CI/CD

- [x] 1.1 Adicionar `tests` ao `sparse-checkout` em `.github/workflows/pr-code-validator.yml`
- [x] 1.2 Adicionar `tests` ao `sparse-checkout` em `.github/workflows/release-editor.yml`
- [x] 1.3 Adicionar passo de supressão do WerFault (registro do Windows com `DontShowUI=1` e `Disabled=1`) no `.github/workflows/release-editor.yml`

## 2. Test-Driven Development (TDD) para Ciclo de Vida de Páginas

- [x] 2.1 [TDD - Red] Criar teste em `editor/legacy_views/area_principal_test.py` verificando que a instanciação das páginas não deixa widgets pendentes de `deleteLater()`
- [x] 2.2 [TDD - Green] Refatorar `PaginaBase` em `editor/legacy_views/area_principal.py` para criar `self.label` condicionalmente apenas quando não há layout próprio
- [x] 2.3 [TDD - Green] Remover remoção e chamadas a `deleteLater()` nas páginas `PaginaDados`, `PaginaImagens`, `PaginaMapas` e `PaginaBetas`
- [x] 2.4 [TDD - Refactor] Garantir 100% de cobertura de testes unitários nas classes refatoradas

## 3. Fixture de Teardown e Higienização da Suíte de Testes

- [x] 3.1 Remover bloco de testes duplicados em `editor/legacy_views/area_principal_test.py` (linhas 455 a 640)
- [x] 3.2 Criar fixture `janela_principal` com `yield` e teardown explícito (`janela.close()`) e context manager `criar_janela_teste` em `editor/legacy_views/area_principal_test.py`
- [x] 3.3 Atualizar os testes existentes de `area_principal_test.py` para utilizar a fixture / context manager com teardown garantido

## 4. Validação e Testes de Integração em Primeiro Lugar

- [x] 4.1 Executar a suíte unitária `editor/legacy_views/area_principal_test.py` isoladamente e verificar ausência de falhas, avisos ou vazamentos
- [x] 4.2 Executar os testes de integração e conformidade de `tests/` (`tipagem_estatica_test.py` e `validador_tipagem_test.py`)
- [x] 4.3 Executar a suíte inteira de 1.263 testes localmente simulando as restrições do CI (`uv run pytest -n 2 --dist=loadfile`) e atestar 100% de aprovação