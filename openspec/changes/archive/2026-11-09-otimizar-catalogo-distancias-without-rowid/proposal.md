## Why

Na estrutura atual de `sql/catalogo.sql`, a tabela `catalogo_distancias_estrada` declara `PRIMARY KEY (croqui_uid, no_osm_id)` sem a cláusula `WITHOUT ROWID` e ainda cria um índice secundário explícito `idx_catalogo_distancias_estrada_no ON catalogo_distancias_estrada(no_osm_id)`. Internamente no SQLite, isso armazena os mesmos dados em **três árvores B-Tree separadas** (a tabela ROWID padrão com `rowid` de 64 bits oculto, o `sqlite_autoindex` duplicando `(croqui_uid, no_osm_id, rowid)` e o índice secundário `idx_catalogo_distancias_estrada_no`). Como o aplicativo móvel (`RepositorioCatalogo.carregarMalhaEstrada`) realiza uma leitura única da tabela para construir a KD-Tree 2D em memória e nunca filtra `WHERE no_osm_id = ?` no SQLite, adicionar `WITHOUT ROWID` e remover `idx_catalogo_distancias_estrada_no` reduz o tamanho em disco de `catalogo_distancias_estrada` pela metade (~50,5% menor no `.db` e ~48,6% menor em `.db.gz`), sem alterar nenhuma coluna lógica nem o contrato de sincronização JSON (`/sync`).

## What Changes

- **Tabela Clusterizada `WITHOUT ROWID` e Remoção de Índice Redundante (`aresta_api/sql/catalogo.sql`)**:
  - Alterar a definição de `catalogo_distancias_estrada` em `aresta_api/sql/catalogo.sql` para `PRIMARY KEY (croqui_uid, no_osm_id)) WITHOUT ROWID;`.
  - Remover `CREATE INDEX IF NOT EXISTS idx_catalogo_distancias_estrada_no ON catalogo_distancias_estrada(no_osm_id);` de `aresta_api/sql/catalogo.sql`.
  - Regenerar os artefatos SQL multi-linguagem (`catalogo_sql.py`, `catalogo_sql.dart`, `catalogo_sql.ts`) e atualizar os testes de contrato em `aresta_api` (`src/gerador_sql_test.py` e `build_test.py`).
- **Inicializador, Migração Automática In-Place e Sincronizador D1 (`aresta_db`)**:
  - Atualizar `inicializar_banco_catalogo` (`scripts/gerar_catalogo_sqlite_lib.py`) para não exigir `idx_catalogo_distancias_estrada_no` em `objetos_esperados` e migrar automaticamente bancos `catalogo.db` pré-existentes para `WITHOUT ROWID` (preservando linhas existentes, removendo `idx_catalogo_distancias_estrada_no` e executando `VACUUM`).
  - Atualizar `serving/sincronizar_d1_lib.py` (e `serving/sincronizar_d1_lib_test.py`) removendo a importação/execução de `DDL_INDICE_IDX_CATALOGO_DISTANCIAS_ESTRADA_NO` e executando `DROP INDEX IF EXISTS idx_catalogo_distancias_estrada_no` na inicialização do schema D1.
- **Consumo e Migração Local no Aplicativo Móvel (`aresta_app`)**:
  - Sincronizar o submódulo `frontend/lib/aresta_api` no `aresta_app` com os artefatos gerados (`catalogo_sql.dart` e `croqui.pb.dart`).
  - No `onOpen` de `RepositorioCatalogo._obterBanco` (`frontend/lib/services/catalogo/repositorio_catalogo.dart`), remover o índice legado `idx_catalogo_distancias_estrada_no` e migrar `catalogo_distancias_estrada` in-place para `WITHOUT ROWID` caso o dispositivo possua um `catalogo.db` local criado antes desta otimização, validando o comportamento em `frontend/test/services/catalogo/repositorio_catalogo_test.dart`.

## Capabilities

### New Capabilities
- *(Nenhuma nova capability)*

### Modified Capabilities
- `catalogo-sqlite-delta-sync`: Atualização do requisito de indexação, chaves primárias e sincronização D1/cliente de `catalogo_distancias_estrada` para exigir armazenamento clusterizado `WITHOUT ROWID` sem índice secundário redundante em `no_osm_id`, com migração in-place automática de bancos existentes no pipeline, no D1 e no aplicativo móvel.

## Impact

- **`aresta_api`**: `sql/catalogo.sql`, artefatos gerados em `sql/generated/` (`python`, `dart`, `ts`), `src/gerador_sql_test.py` e `build_test.py`.
- **`aresta_db`**: `scripts/gerar_catalogo_sqlite_lib.py`, `scripts/gerar_catalogo_sqlite_lib_test.py`, `serving/sincronizar_d1_lib.py`, `serving/sincronizar_d1_lib_test.py` e `docs/catalogo_sqlite_e_delta_sync.md`.
- **`aresta_app`**: submódulo `frontend/lib/aresta_api`, `frontend/lib/services/catalogo/repositorio_catalogo.dart` e `frontend/test/services/catalogo/repositorio_catalogo_test.dart`.
