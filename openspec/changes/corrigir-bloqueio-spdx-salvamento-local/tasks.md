## 1. Emissão Nativa de Comentários SPDX no Frontmatter e YAML (TDD)

- [ ] 1.1 (TDD) Escrever testes em `editor/models/croqui_model_test.py` verificando que `_salvar_objeto_com_frontmatter` grava os comentários SPDX e Copyright no topo do frontmatter gerado
- [ ] 1.2 Atualizar `_salvar_objeto_com_frontmatter` em `editor/models/croqui_model.py` para emitir os comentários SPDX e Copyright logo abaixo de `---`
- [ ] 1.3 (TDD) Escrever testes em `scripts/preparar_submissao_lib_test.py` verificando que `salvar_md_com_frontmatter` grava os comentários SPDX e Copyright no topo do frontmatter
- [ ] 1.4 Atualizar `salvar_md_com_frontmatter` em `scripts/preparar_submissao_lib.py` para emitir os comentários SPDX e Copyright
- [ ] 1.5 (TDD) Escrever testes em `editor/core/worker_test.py` verificando que `TarefaSalvamento` grava `croqui.yaml` com os comentários SPDX e Copyright no topo
- [ ] 1.6 Atualizar `TarefaSalvamento.run` em `editor/core/worker.py` para prefixar o dump de `croqui.yaml` com os comentários SPDX e Copyright

## 2. Resiliência e Retentativa a Bloqueios Transitórios no Windows (TDD)

- [ ] 2.1 (TDD) Escrever testes em `scripts/preparar_submissao_lib_test.py` simulando falhas transitórias com `OSError` (`[Errno 22]` e `[Errno 13]`) em `garantir_comentarios_licenca` e verificando política de retentativa e sucesso após retry
- [ ] 2.2 Implementar loop de retentativa com backoff linear/exponencial e captura de `OSError` em `garantir_comentarios_licenca` em `scripts/preparar_submissao_lib.py`

## 3. Validação de Integração e Cobertura

- [ ] 3.1 Executar os testes de integração do salvamento e compilação no editor (`pytest editor/models/croqui_model_test.py scripts/preparar_submissao_lib_test.py editor/core/worker_test.py`)
- [ ] 3.2 Executar a suíte completa de testes e verificar conformidade com 100% de cobertura nos arquivos alterados
