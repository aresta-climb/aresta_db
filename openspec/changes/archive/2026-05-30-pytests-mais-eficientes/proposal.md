## Why

Atualmente, o comando `build.py test` executa todos os 252 testes unitários e de integração de forma sequencial, levando cerca de 34 segundos. À medida que o projeto cresce, esse feedback lento desencoraja a execução constante dos testes no desenvolvimento local. Precisamos de um mecanismo que evite re-executar testes cujos arquivos de dependência não mudaram e que permita rodar a suite em paralelo de forma estável.

## What Changes

- Adição das dependências `pytest-testmon` (para execução incremental baseada em impacto) e `pytest-xdist` (para paralelização de testes em múltiplos cores) ao `requirements.txt`.
- Correção de falha de segmentação (exit code 1) no teste `editor/core/servidor_celular_test.py::test_deve_gerar_qr_code_em_memoria` ao rodar em paralelo/ambiente isolado, injetando o fixture `qapp`.
- Aprimoramento do script de build (`build.py`) para suportar e configurar automaticamente as execuções aceleradas via `--testmon` e em paralelo (`-n auto`).

## Capabilities

### New Capabilities

- `test-pipeline-optimization`: Otimização da velocidade de execução e estabilidade paralela dos testes unitários e de integração locais.

### Modified Capabilities

Nenhuma.

## Impact

- **Ambiente de Desenvolvimento**: Inclusão de `pytest-testmon` e `pytest-xdist` no `requirements.txt`.
- **Ferramentas de Build**: Modificação no `build.py` para permitir parametrização das melhorias de teste.
- **Suite de Testes**: Ajuste estrutural em `editor/core/servidor_celular_test.py` para compatibilidade com execução paralela isolada.
