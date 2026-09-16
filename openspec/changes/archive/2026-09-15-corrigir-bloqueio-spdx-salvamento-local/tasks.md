## 1. Emissão Nativa de Comentários SPDX no Frontmatter e YAML (TDD)

- [x] 1.1 (TDD) Escrever testes em `editor/models/croqui_model_test.py` verificando que `_salvar_objeto_com_frontmatter` grava os comentários SPDX e Copyright no topo do frontmatter gerado
- [x] 1.2 Atualizar `_salvar_objeto_com_frontmatter` em `editor/models/croqui_model.py` para emitir os comentários SPDX e Copyright logo abaixo de `---`
- [x] 1.3 (TDD) Escrever testes em `scripts/preparar_submissao_lib_test.py` verificando que `salvar_md_com_frontmatter` grava os comentários SPDX e Copyright no topo do frontmatter
- [x] 1.4 Atualizar `salvar_md_com_frontmatter` em `scripts/preparar_submissao_lib.py` para emitir os comentários SPDX e Copyright
- [x] 1.5 (TDD) Escrever testes em `editor/core/worker_test.py` verificando que `TarefaSalvamento` grava `croqui.yaml` com os comentários SPDX e Copyright no topo
- [x] 1.6 Atualizar `TarefaSalvamento.run` em `editor/core/worker.py` para prefixar o dump de `croqui.yaml` com os comentários SPDX e Copyright

## 2. Resiliência e Retentativa a Bloqueios Transitórios no Windows (TDD)

- [x] 2.1 (TDD) Escrever testes em `scripts/preparar_submissao_lib_test.py` simulando falhas transitórias com `OSError` (`[Errno 22]` e `[Errno 13]`) em `garantir_comentarios_licenca` e verificando política de retentativa e sucesso após retry
- [x] 2.2 Implementar loop de retentativa com backoff linear/exponencial e captura de `OSError` em `garantir_comentarios_licenca` em `scripts/preparar_submissao_lib.py`

## 3. Validação de Integração e Cobertura

- [x] 3.1 Executar os testes de integração do salvamento e compilação no editor (`pytest editor/models/croqui_model_test.py scripts/preparar_submissao_lib_test.py editor/core/worker_test.py`)
- [x] 3.2 Executar a suíte completa de testes e verificar conformidade com 100% de cobertura nos arquivos alterados
