## 1. Testes de Integração de Fronteira e Módulos Legados (Princípio V)

- [ ] 1.1 Excluir o teste de integração de ponta a ponta `editor/core/workflow_export_import_test.py`
- [ ] 1.2 Excluir o módulo de biblioteca `editor/core/croqui_format.py` e seu respectivo teste unitário `editor/core/croqui_format_test.py`
- [ ] 1.3 Excluir o script utilitário legado `scripts/gerar_croqui_experimental.py` e seus testes `scripts/gerar_croqui_experimental_test.py` e `scripts/test_integracao_gerar_croqui.py`

## 2. Núcleo do Editor: TDD e 100% de Cobertura (Princípios II, III, IV)

- [ ] 2.1 (TDD Vermelho) Atualizar `editor/core/croqui_experimental_test.py` removendo testes de exportação e importação de arquivos `.croqui`
- [ ] 2.2 (TDD Verde) Remover os métodos `exportar_croqui`, `importar_croqui` e importações associadas em `editor/core/croqui_experimental.py`
- [ ] 2.3 (TDD Verde) Remover a classe de worker assíncrono `TarefaExportacao` em `editor/core/worker.py`
- [ ] 2.4 (TDD Refatorar) Executar `pytest editor/core/croqui_experimental_test.py editor/core/worker_test.py --cov` certificando 100% de aprovação e cobertura

## 3. Interface Gráfica do Editor Desktop: TDD (Princípios III, IV, VII)

- [ ] 3.1 (TDD Vermelho) Atualizar `editor/legacy_views/area_principal_test.py` removendo asserções da ação `acao_exportar` e método `exportar_croqui`
- [ ] 3.2 (TDD Verde) Remover a ação `acao_exportar`, o botão na barra superior e o método `exportar_croqui` em `editor/legacy_views/area_principal.py`
- [ ] 3.3 (TDD Vermelho) Atualizar `editor/legacy_views/tela_de_carregamento_test.py` removendo testes do botão "Importar Croqui" e diálogo de seleção de arquivo
- [ ] 3.4 (TDD Verde) Remover o botão "Importar Croqui" e o manipulador `ao_clicar_importar` em `editor/legacy_views/tela_de_carregamento.py`
- [ ] 3.5 (TDD Refatorar) Executar os testes de views garantindo que o histórico de comandos e todas as demais funcionalidades permaneçam íntegras

## 4. Validador de Pull Requests como Biblioteca Pura (Princípios II, III, IV, V)

- [ ] 4.1 (TDD Vermelho) Atualizar `serving/pr_db_validator_test.py` para validar o novo contrato da biblioteca sem geração de `.croqui`, cobrindo cenários de sucesso e erro na compilação
- [ ] 4.2 (TDD Verde) Refatorar a biblioteca `serving/pr_db_validator.py` consumindo diretamente a rotina `deploy(...)` e retornando mensagens de erro sem criar arquivos em disco
- [ ] 4.3 (TDD Refatorar) Executar `pytest serving/pr_db_validator_test.py --cov` garantindo 100% de cobertura de unidade na biblioteca
- [ ] 4.4 (CI/CD) Atualizar o arquivo `.github/workflows/pr-db-validator.yml` removendo credenciais de S3/R2, passos do AWS CLI e upload de artefatos

## 5. Configurações, Tipagem Estática e Certificação Final (Princípios I, III, IV, VI)

- [ ] 5.1 Remover a associação de arquivo binário `*.croqui binary` do arquivo `.gitattributes`
- [ ] 5.2 Atualizar documentações que mencionem o empacotamento `.croqui` (incluindo `aresta_api/README.md`)
- [ ] 5.3 Executar o teste guardião `tests/tipagem_estatica_test.py` garantindo zero erros MyPy estrito e conformidade total de AST
- [ ] 5.4 Executar a suíte completa de testes do repositório (`pytest`) certificando 100% de aprovação e ausência de regressões
