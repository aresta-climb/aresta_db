# Tarefas para Implementação: SPDX Injection via Comentários

## 1. Testes (TDD)
- [ ] 1.1 Criar a pasta `tests/fixtures/spdx_comments` com arquivos mockados (`.yaml` e `.md` com e sem frontmatter, com e sem comentário SPDX)
- [ ] 1.2 Criar testes em `tests/test_spdx_comments.py` validando todos os cenários.
- [ ] 1.3 Executar testes e garantir que falham inicialmente (TDD - Red)

## 2. Implementação Core
- [ ] 2.1 Criar função `garantir_spdx_comentario` em `scripts/preparar_submissao_lib.py` que injeta o comentário `# SPDX-License-Identifier: ODbL-1.0`
- [ ] 2.2 Integrar a função no final de `corrigir_database` varrendo `.yaml` e `.md` do pico.
- [ ] 2.3 Executar os testes e garantir que passam (TDD - Green)

## 3. Validação e Deploy
- [ ] 3.1 Executar `python scripts/deploy_generated.py` localmente
- [ ] 3.2 Verificar as modificações com `git diff`
- [ ] 3.3 Confirmar que o Protobuf não foi afetado e a injeção é idempotente.
