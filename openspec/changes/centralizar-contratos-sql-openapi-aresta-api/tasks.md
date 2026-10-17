# Tasks

## 1. Migração do `aresta_api` para `uv` e Estrutura Library-First (`src/`)

- [ ] 1.1 Criar `aresta_api/pyproject.toml` com as dependências de build, validação e qualidade (`grpcio-tools`, `mypy-protobuf`, `openapi-spec-validator`, `pyyaml`, `types-PyYAML`, `pytest`, `pytest-cov`, `ruff`, `mypy`), gerar `aresta_api/uv.lock` via `uv lock` e remover `aresta_api/requirements.txt` (verificar executando `uv run pytest` e `uv run mypy --strict` no `aresta_api`).
- [ ] 1.2 Estruturar o pacote `aresta_api/src/` e atualizar `aresta_api/README.md` documentando o fluxo com `uv` e a arquitetura de contratos `proto/`, `sql/` e `openapi/`.

## 2. Biblioteca Geradora de Contratos SQL (`aresta_api/src/gerador_sql.py`) e Esquemas `.sql`

- [ ] 2.1 Escrever os testes de comportamento em `aresta_api/src/gerador_sql_test.py` (ciclo Red) cobrindo validação em SQLite `:memory:`, extração de tabelas/colunas/nulabilidade via `PRAGMA table_info`, rejeição de SQL inválido e emissão determinística de código Python (`TypedDict` + constantes DDL), Dart (classes `fromMap`/`toMap` + constantes DDL) e TypeScript (`interface` + constantes DDL).
- [ ] 2.2 Implementar `aresta_api/src/gerador_sql.py` (ciclo Green/Refactor) atingindo 100% de cobertura comportamental em `gerador_sql_test.py` e aprovação em `ruff check` e `mypy --strict`.
- [ ] 2.3 Criar `aresta_api/sql/catalogo.sql` (tabelas `catalogo_croquis`, `catalogo_aresta`, `catalogo_meta` e índices) e `aresta_api/sql/catalogo_d1.sql` (tabela `deltas_catalogo` e índice de versão), validando a geração dos artefatos em `aresta_api/sql/generated/{python,dart,ts}/`.

## 3. Biblioteca Geradora de Contratos OpenAPI 3.1 (`aresta_api/src/gerador_openapi.py`) e Especificações `.yaml`

- [ ] 3.1 Escrever os testes de comportamento em `aresta_api/src/gerador_openapi_test.py` (ciclo Red) cobrindo validação formal com `openapi-spec-validator`, rejeição de especificações OpenAPI 3.1 inválidas e emissão de constantes de `servers` (URLs base), constantes de `paths` (rotas HTTP) e estruturas tipadas (`TypedDict` em Python, classes DTO `fromJson`/`toJson` em Dart e `interface`/`type` em TypeScript) a partir de `components/schemas` e parâmetros de query/path.
- [ ] 3.2 Implementar `aresta_api/src/gerador_openapi.py` (ciclo Green/Refactor) atingindo 100% de cobertura comportamental em `gerador_openapi_test.py` e aprovação em `ruff check` e `mypy --strict`.
- [ ] 3.3 Criar as especificações OpenAPI 3.1 em `aresta_api/openapi/catalogo.yaml`, `aresta_api/openapi/previa.yaml`, `aresta_api/openapi/colaboracao.yaml` e `aresta_api/openapi/feedback.yaml` com todas as URLs de produção, rotas, query/path parameters e schemas de request/response do `aresta_backend`, validando a geração em `aresta_api/openapi/generated/{python,dart,ts}/`.

## 4. Biblioteca Validadora de Paridade SQL ↔ OpenAPI (`aresta_api/src/validador_paridade.py`) e `build.py`

- [ ] 4.1 Escrever os testes de comportamento em `aresta_api/src/validador_paridade_test.py` (ciclo Red) verificando a correspondência exata 1:1 de colunas, tipos e nulabilidade entre tabelas SQLite (`PRAGMA table_info`) e schemas OpenAPI (`CatalogoCroqui` ↔ `catalogo_croquis` e `CatalogoEntidade` ↔ `catalogo_aresta`), incluindo cenários de falha quando há divergência de coluna, tipo ou obrigatoriedade.
- [ ] 4.2 Implementar `aresta_api/src/validador_paridade.py` (ciclo Green/Refactor) atingindo 100% de cobertura comportamental e aprovação em `ruff check` e `mypy --strict`.
- [ ] 4.3 Refatorar `aresta_api/build.py` (e criar seu teste espelhado `aresta_api/build_test.py`) para orquestrar a compilação de `proto/`, `sql/` e `openapi/`, executar a validação de paridade SQL ↔ OpenAPI e atualizar o hash de sincronização; executar `uv run python build.py` para gerar todos os artefatos em `aresta_api/sql/generated/` e `aresta_api/openapi/generated/`.

## 5. Integração dos Contratos Gerados em `aresta_db` e `aresta_backend`

- [ ] 5.1 Atualizar `aresta_db/scripts/gerar_catalogo_sqlite.py`, `aresta_db/scripts/gerar_deltas_catalogo.py` e `aresta_db/serving/sincronizar_d1_lib.py` para importar o DDL canônico e os `TypedDict` gerados em `aresta_api/sql/generated/python/` e `aresta_api/openapi/generated/python/`, mantendo todos os testes existentes (`*_test.py`), `ruff check` e `mypy --strict` 100% verdes.
- [ ] 5.2 Atualizar `aresta_db/src/editor/submissao.py` e `aresta_db/src/editor/previa_remota.py` para consumir as constantes de rotas e tipos de payload gerados em `aresta_api/openapi/generated/python/` (`colaboracao_openapi.py` e `previa_openapi.py`), verificando que `submissao_test.py` e `previa_remota_test.py` passam com 100% de cobertura.
- [ ] 5.3 Atualizar os Cloudflare Workers (`catalogo`, `previa`, `feedback`) e as Supabase Edge Functions (`create-pr`, `git-proxy`, `app-feedback`, `discord-feedback`) em `../aresta_backend` para importar as interfaces TypeScript, rotas e DDL gerados pelo `aresta_api`, confirmando que todas as 4 suítes `deno test` continuam passando integralmente.
