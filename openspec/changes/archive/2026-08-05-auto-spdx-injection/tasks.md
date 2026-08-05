# Tarefas para Implementação: SPDX Injection via Comentários

## 1. Testes (TDD)
- [x] 1.1 Criar a pasta `tests/fixtures/spdx_comments` com arquivos mockados (`.yaml` e `.md` com e sem frontmatter, com e sem comentário SPDX)
- [x] 1.2 Criar testes em `tests/test_spdx_comments.py` validando todos os cenários.
- [x] 1.3 Executar testes e garantir que falham inicialmente (TDD - Red)

## 2. Implementação Core
- [x] 2.1 Criar função `garantir_comentarios_licenca` em `scripts/preparar_submissao_lib.py` que injeta o comentário SPDX e o Copyright
- [x] 2.2 Integrar a função no final de `corrigir_database` varrendo `.yaml` e `.md` do pico.
- [x] 2.3 Executar os testes e garantir que passam (TDD - Green)

## 3. Validação e Deploy
- [x] 3.1 Executar `python scripts/deploy_generated.py` localmente
- [x] 3.2 Verificar as modificações com `git diff`
- [x] 3.3 Confirmar que o Protobuf não foi afetado e a injeção é idempotente.
