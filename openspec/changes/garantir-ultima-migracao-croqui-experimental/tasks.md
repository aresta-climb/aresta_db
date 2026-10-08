# Tasks

## 1. Resolução Resiliente do Caminho de Migrações

- [ ] 1.1 [TDD] Adicionar testes unitários em `scripts/migrador_test.py` para a função `obter_caminho_migracoes` cobrindo cenários padrão, `sys.frozen` com `sys._MEIPASS` e fallback para `GerenciadorCaminhos().obter_caminho_base_repo()`.
- [ ] 1.2 Implementar a função `obter_caminho_migracoes` em `scripts/migrador.py` e integrá-la nas funções `aplicar_migracoes` e `obter_ultima_versao_migracao`, validando a passagem dos testes com `pytest scripts/migrador_test.py`.

## 2. Empacotamento do Diretório de Migrações no Editor

- [ ] 2.1 Atualizar `editor/EditorAresta.spec` para incluir a pasta `migracoes/` nos `datas` empacotados pelo PyInstaller.
- [ ] 2.2 Adicionar teste unitário em `editor/build_test.py` verificando que a pasta `migracoes` está presente nas definições de dados do spec de empacotamento e validar com `pytest editor/build_test.py`.

## 3. Garantia de Versão em Croquis Experimentais e Submissão

- [ ] 3.1 [TDD] Adicionar teste unitário em `scripts/preparar_submissao_lib_test.py` garantindo que `corrigir_database` atualiza `ultima_migracao` para `obter_ultima_versao_migracao()` quando o croqui estiver zerado, ausente ou defasado.
- [ ] 3.2 Atualizar `corrigir_database` em `scripts/preparar_submissao_lib.py` para forçar a atualização de `ultima_migracao` para a versão máxima do catálogo e validar com `pytest scripts/preparar_submissao_lib_test.py`.
- [ ] 3.3 [TDD] Adicionar teste em `editor/core/croqui_experimental_test.py` garantindo que croquis criados do zero ou a partir de oficial preservem/registrem `ultima_migracao == obter_ultima_versao_migracao()`.
- [ ] 3.4 Ajustar `GerenciadorCroquiExperimental` em `editor/core/croqui_experimental.py` conforme necessário e validar com `pytest editor/core/croqui_experimental_test.py`.

## 4. Validação de Migração no CI (pr_db_validator)

- [ ] 4.1 [TDD] Adicionar testes unitários em `serving/pr_db_validator_test.py` cobrindo a verificação de `ultima_migracao` em pastas modificadas do database (rejeitando valores menores que a versão atual e aprovando valores iguais).
- [ ] 4.2 Implementar `validar_versoes_migracao` em `serving/pr_db_validator.py` e integrá-lo à execução de `validar_pull_request`, validando com `pytest serving/pr_db_validator_test.py`.
- [ ] 4.3 Atualizar `.github/workflows/pr-db-validator.yml` incluindo `migracoes` no bloco de `sparse-checkout`.

## 5. Verificação Geral e Cobertura

- [ ] 5.1 Executar a suíte completa de testes dos módulos alterados (`pytest scripts/migrador_test.py editor/build_test.py scripts/preparar_submissao_lib_test.py serving/pr_db_validator_test.py editor/core/croqui_experimental_test.py`) e verificar cobertura de 100%.
