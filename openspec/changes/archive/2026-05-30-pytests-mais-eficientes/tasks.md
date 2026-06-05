## 1. Ajustes de Dependências e Testes Existentes

- [x] 1.1 Adicionar `pytest-testmon` e `pytest-xdist` ao [requirements.txt](file:///c:/Renato/Devel/aresta/aresta_db/requirements.txt).
- [x] 1.2 Corrigir o teste `test_deve_gerar_qr_code_em_memoria` em [servidor_celular_test.py](file:///c:/Renato/Devel/aresta/aresta_db/editor/core/servidor_celular_test.py) adicionando o fixture `qapp`.

## 2. Aprimoramento do Script de Build

- [x] 2.1 Adicionar novas opções no parser de argumentos do [build.py](file:///c:/Renato/Devel/aresta/aresta_db/build.py): `--testmon`, `--parallel` e `--drop-cache`.
- [x] 2.2 Atualizar a função `run_tests` no [build.py](file:///c:/Renato/Devel/aresta/aresta_db/build.py) para passar os argumentos adequados para o `pytest` se as flags estiverem habilitadas.
- [x] 2.3 Implementar a limpeza do cache de banco do testmon (`.testmondata`) quando a flag `--drop-cache` (ou `--force`) for passada.

## 3. Validação e Verificação

- [x] 3.1 Executar a suite de testes completa localmente para garantir compatibilidade com paralelização (`-n auto`).
- [x] 3.2 Executar a suite de testes incrementalmente (`--testmon`) para garantir que o cache de impacto funciona perfeitamente.
