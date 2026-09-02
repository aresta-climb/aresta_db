## 1. Remoção de Módulos e Testes Legados

- [ ] 1.1 Excluir o módulo `editor/core/croqui_format.py` e seu teste unitário `editor/core/croqui_format_test.py`
- [ ] 1.2 Excluir o script utilitário `scripts/gerar_croqui_experimental.py` e seus testes `scripts/gerar_croqui_experimental_test.py` e `scripts/test_integracao_gerar_croqui.py`
- [ ] 1.3 Excluir o teste de integração legado `editor/core/workflow_export_import_test.py`

## 2. Refatoração do Núcleo do Editor (Core e Workers)

- [ ] 2.1 Atualizar `editor/core/croqui_experimental_test.py`, eliminando testes de `exportar_croqui` e `importar_croqui` e mantendo 100% de cobertura nos métodos remanescentes
- [ ] 2.2 Remover os métodos `exportar_croqui` e `importar_croqui` e imports associados em `editor/core/croqui_experimental.py`
- [ ] 2.3 Remover a classe de worker `TarefaExportacao` em `editor/core/worker.py`

## 3. Refatoração da Interface Gráfica do Editor (Views)

- [ ] 3.1 Atualizar `editor/legacy_views/area_principal_test.py` removendo asserções da ação de exportar `.croqui`
- [ ] 3.2 Remover a ação `acao_exportar`, o ícone e o método `exportar_croqui` em `editor/legacy_views/area_principal.py`
- [ ] 3.3 Atualizar `editor/legacy_views/tela_de_carregamento_test.py` removendo asserções e testes do fluxo de importação
- [ ] 3.4 Remover o botão "Importar Croqui" e seu método `ao_clicar_importar` em `editor/legacy_views/tela_de_carregamento.py`

## 4. Refatoração do Validador de PRs e CI/CD

- [ ] 4.1 Atualizar `serving/pr_db_validator_test.py` para verificar a validação de cabeçalhos/licenças e compilação de teste sem gerar `.croqui`
- [ ] 4.2 Refatorar `serving/pr_db_validator.py` eliminando chamadas a `gerar_croqui_experimental` e adicionando verificação direta via `deploy(...)`
- [ ] 4.3 Atualizar `.github/workflows/pr-db-validator.yml` removendo os passos de upload para Cloudflare R2 e geração de links de download em comentários

## 5. Limpeza de Configurações, Documentação e Validação Final

- [ ] 5.1 Remover a regra `*.croqui binary` do arquivo `.gitattributes`
- [ ] 5.2 Limpar menções a empacotamento `.croqui` no arquivo `aresta_api/README.md`
- [ ] 5.3 Executar a suíte de testes com `pytest` e verificar aprovação completa e integridade de cobertura
