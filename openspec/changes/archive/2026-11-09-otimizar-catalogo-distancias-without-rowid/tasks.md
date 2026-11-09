## 1. Esquema Canônico SQL e Artefatos Gerados (`aresta_api`)

- [x] 1.1 Em `aresta_api/sql/catalogo.sql`, adicionar `WITHOUT ROWID` à definição de `catalogo_distancias_estrada` e remover `CREATE INDEX IF NOT EXISTS idx_catalogo_distancias_estrada_no`, regenerar `sql/generated/` (`python`, `dart`, `ts`) via `uv run python build.py`, e atualizar `aresta_api/src/gerador_sql_test.py` e `aresta_api/build_test.py` (TDD Red-Green-Refactor, 100% de cobertura).

## 2. Inicializador do `catalogo.db` e Sincronizador D1 (`aresta_db`)

- [x] 2.1 Em `scripts/gerar_catalogo_sqlite_lib.py`, remover `idx_catalogo_distancias_estrada_no` de `objetos_esperados` em `inicializar_banco_catalogo` e implementar a migração in-place automática (com `VACUUM`) quando um banco existente possuir `catalogo_distancias_estrada` sem `WITHOUT ROWID` ou contiver o índice legado `idx_catalogo_distancias_estrada_no`, adicionando testes de comportamento em `scripts/gerar_catalogo_sqlite_lib_test.py` e atualizando `docs/catalogo_sqlite_e_delta_sync.md` (100% de cobertura).
- [x] 2.2 Em `serving/sincronizar_d1_lib.py`, remover o uso de `DDL_INDICE_IDX_CATALOGO_DISTANCIAS_ESTRADA_NO` e emitir `DROP INDEX IF EXISTS idx_catalogo_distancias_estrada_no` em `inicializar_schema_d1`, atualizando `serving/sincronizar_d1_lib_test.py` (100% de cobertura).

## 3. Submódulo `aresta_api` e Migração Local no Aplicativo (`aresta_app`)

- [x] 3.1 Atualizar o submódulo `frontend/lib/aresta_api` em `aresta_app` com os novos artefatos Dart (`catalogo_sql.dart` e `croqui.pb.dart`).
- [x] 3.2 Em `frontend/lib/services/catalogo/repositorio_catalogo.dart`, atualizar o `onOpen` de `_obterBanco` para remover `idx_catalogo_distancias_estrada_no` e converter `catalogo_distancias_estrada` existente sem `WITHOUT ROWID` preservando seus registros, adicionando teste de comportamento correspondente em `frontend/test/services/catalogo/repositorio_catalogo_test.dart` (TDD Red-Green-Refactor, 100% de cobertura).
