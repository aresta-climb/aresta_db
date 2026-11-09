## Context

No banco SQLite `catalogo.db`:
1. `catalogo_nos_estrada` declara `no_osm_id INTEGER PRIMARY KEY, latitude_e7 INTEGER NOT NULL, longitude_e7 INTEGER NOT NULL`. No SQLite, uma coluna `INTEGER PRIMARY KEY` atua como alias direto para o `ROWID` da B-Tree da tabela, armazenando cada nó OSM único de forma compacta (~16 bytes por nó) sem criar índice separado.
2. `catalogo_distancias_estrada` declara `PRIMARY KEY (croqui_uid, no_osm_id)` sem `WITHOUT ROWID`, além de `CREATE INDEX idx_catalogo_distancias_estrada_no ON catalogo_distancias_estrada(no_osm_id)`. Como a chave primária é composta, a ausência de `WITHOUT ROWID` faz o SQLite alocar um `rowid` oculto de 64 bits na B-Tree principal e duplicar `(croqui_uid, no_osm_id, rowid)` inteiro numa segunda B-Tree (`sqlite_autoindex_catalogo_distancias_estrada_1`), enquanto `idx_catalogo_distancias_estrada_no` cria uma terceira B-Tree `(no_osm_id, rowid)`.

Em benchmark real com 50 croquis, 15.000 nós únicos e 25.000 pares `(croqui_uid, no_osm_id)`:
- **Esquema atual (`ROWID` + autoindex PK + `idx_no`)**: `2.036 KB` descomprimido (`506 KB` Gzip).
- **`WITHOUT ROWID` com `PRIMARY KEY (croqui_uid, no_osm_id)` (sem `idx_no`)**: `1.008 KB` descomprimido (`260 KB` Gzip) — **redução de 50,5% em disco e 48,6% em Gzip**.

## Goals / Non-Goals

**Goals:**
- Converter `catalogo_distancias_estrada` em tabela clusterizada `WITHOUT ROWID` com `PRIMARY KEY (croqui_uid, no_osm_id)` em `aresta_api/sql/catalogo.sql` e regenerar os contratos (`python`, `dart`, `ts`).
- Eliminar o índice secundário redundante `idx_catalogo_distancias_estrada_no` no `aresta_api`, no pipeline `aresta_db` (`gerar_catalogo_sqlite_lib.py` e `serving/sincronizar_d1_lib.py`) e no `aresta_app` (`RepositorioCatalogo`).
- Migrar de forma transparente e determinística qualquer arquivo `catalogo.db` pré-existente que ainda utilize o layout antigo, tanto no pipeline `aresta_db` quanto na abertura do banco local no `aresta_app`.

**Non-Goals:**
- Alterar nomes ou tipos de colunas de `catalogo_distancias_estrada` ou o contrato OpenAPI (`openapi/catalogo.yaml`).
- Adicionar estimativa de tempo de viagem nesta mudança (será discutido separadamente após esta otimização).

## Decisions

### 1. Chave primária clusterizada `PRIMARY KEY (croqui_uid, no_osm_id) WITHOUT ROWID`
- **Decisão**: Manter a ordem `(croqui_uid, no_osm_id)` na `PRIMARY KEY` com `WITHOUT ROWID`.
- **Racional**:
  - Todas as mutações incrementais por croqui (`DELETE FROM catalogo_distancias_estrada WHERE croqui_uid = ?` e `SELECT ... WHERE croqui_uid = ? ORDER BY no_osm_id`) utilizam diretamente o prefixo da chave primária clusterizada em $O(\log N)$ sem precisar de nenhum índice adicional.
  - Agrupar fisicamente as linhas do mesmo `croqui_uid` nas páginas de 4 KB da B-Tree melhora a taxa de compressão Gzip/Brotli na CDN e no pacote APK/IPA (`260 KB` vs `273 KB` se ordenado por `no_osm_id` primeiro).

### 2. Migração in-place em `aresta_db` (`inicializar_banco_catalogo` e `sincronizar_d1_lib.py`) e `aresta_app` (`RepositorioCatalogo`)
- **Decisão**:
  1. Em `inicializar_banco_catalogo` (`scripts/gerar_catalogo_sqlite_lib.py`): inspecionar `SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'catalogo_distancias_estrada'`. Se a tabela existir sem `"WITHOUT ROWID"`, copiar as linhas em memória, executar `DROP TABLE catalogo_distancias_estrada`, recriar com o DDL canônico (`WITHOUT ROWID`), reinserir as linhas e executar `VACUUM`. Se `idx_catalogo_distancias_estrada_no` existir, executar `DROP INDEX IF EXISTS idx_catalogo_distancias_estrada_no` e `VACUUM`.
  2. Em `inicializar_schema_d1` (`serving/sincronizar_d1_lib.py`): remover `DDL_INDICE_IDX_CATALOGO_DISTANCIAS_ESTRADA_NO` e executar `DROP INDEX IF EXISTS idx_catalogo_distancias_estrada_no`.
  3. Em `RepositorioCatalogo._obterBanco` (`frontend/lib/services/catalogo/repositorio_catalogo.dart`): no callback `onOpen`, verificar via `sqlite_master` se `catalogo_distancias_estrada` existe sem `WITHOUT ROWID`; caso positivo, migrar os registros para a nova tabela `WITHOUT ROWID` e executar `DROP INDEX IF EXISTS idx_catalogo_distancias_estrada_no`.
- **Racional**: Garante que tanto o `generated/catalogo.db` quanto o Cloudflare D1 e bancos locais já instalados em dispositivos móveis migrem sem perda de dados quando atualizados via Delta Sync (`/sync`).

## Risks / Trade-offs

- **[Consulta de limpeza de nós órfãos `WHERE no_osm_id NOT IN (SELECT DISTINCT no_osm_id FROM catalogo_distancias_estrada)` sem `idx_no`]** → A tabela `catalogo_distancias_estrada` inteira cabe em ~`500 KB` na memória cache do SQLite; um scan sequencial da B-Tree clusterizada `WITHOUT ROWID` para `SELECT DISTINCT no_osm_id` leva menos de `2 ms` durante o build offline e evita carregar `~500 KB` de índice morto para todos os usuários do aplicativo.
