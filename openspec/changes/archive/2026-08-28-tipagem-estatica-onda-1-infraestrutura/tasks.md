# Tarefas de Implementação: Onda 1 - Infraestrutura de Tipagem Estática

## 1. Configuração de Dependências e MyPy Estrito

- [x] 1.1 Adicionar `mypy`, `mypy-protobuf`, `types-requests`, `types-PyYAML` e `types-protobuf` no grupo `dev` do `pyproject.toml` e sincronizar com `uv lock`.
- [x] 1.2 Configurar a seção `[tool.mypy]` no `pyproject.toml` com regras estritas (`strict = true`, `disallow_untyped_defs = true`, `check_untyped_defs = true`, `no_implicit_optional = true`, `warn_return_any = true`).

## 2. Geração de Stubs Tipados para Protobuf (aresta_api)

- [x] 2.1 Criar testes unitários em `aresta_api/build_test.py` para verificar a geração de arquivos de stub `.pyi` acompanhando os arquivos `_pb2.py`.
- [x] 2.2 Modificar `aresta_api/build.py` para incluir o plugin `protoc-gen-mypy` (`--mypy_out`) na compilação de arquivos `.proto`.
- [x] 2.3 Executar o build de protos da `aresta_api` e validar a integridade dos stubs `.pyi` gerados em `aresta_api/proto/generated/`.

## 3. Testes Guardiões de Tipagem no Pytest

- [x] 3.1 Criar módulo de teste `tests/tipagem_estatica_test.py` e biblioteca `tests/validador_tipagem.py` no `aresta_db` executando o MyPy programaticamente (`mypy.api.run`) para validar a ausência de violações de tipo.
- [x] 3.2 Implementar metateste de inspeção de AST em `tests/validador_tipagem_test.py` garantindo que funções e métodos possuem anotações de parâmetros e tipo de retorno.
- [x] 3.3 Executar a suíte de testes com `pytest` e validar que todos os novos testes passam com 100% de cobertura de testes.

