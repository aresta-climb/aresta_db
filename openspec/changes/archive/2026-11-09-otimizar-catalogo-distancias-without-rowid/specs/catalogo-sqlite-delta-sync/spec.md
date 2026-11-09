## MODIFIED Requirements

### Requirement: Estrutura e geração do catálogo SQLite
O pipeline de compilação SHALL gerar um banco de dados SQLite denominado `catalogo.db` contendo as tabelas `catalogo_croquis`, `catalogo_aresta`, `catalogo_nos_estrada`, `catalogo_distancias_estrada` (armazenada como tabela clusterizada `WITHOUT ROWID` sem índice secundário redundante em `no_osm_id`) e `catalogo_meta` definidas pelo esquema canônico `aresta_api/sql/catalogo.sql` (consumido via artefato gerado `aresta_api/sql/generated/catalogo_sql.py`), onde `catalogo_aresta` armazena de forma normalizada todas as entidades endereçáveis por UID (`escalada`, `setor`, `grupo` e `botao`) referenciando `setor_uid` e `grupo_uid` sem duplicar nomes de setores ou grupos, `catalogo_nos_estrada` e `catalogo_distancias_estrada` armazenam a malha rodoviária pré-computada por `croqui_uid`, e o conjunto é versionado por um hash lógico determinístico (`versao_catalogo`) registrado na mensagem `Indice` (`indice.binarypb`).

#### Scenario: Geração bem-sucedida a partir de croquis compilados
- **WHEN** o pipeline de compilação processa a lista de croquis do banco de dados
- **THEN** o arquivo `catalogo.db` é inicializado com o DDL canônico de `aresta_api` e preenchido contendo todos os croquis em `catalogo_croquis`, todas as entidades endereçáveis (`escalada`, `setor`, `grupo` e `botao`) em `catalogo_aresta` e a malha rodoviária em `catalogo_nos_estrada` e `catalogo_distancias_estrada`, além da `versao_catalogo` gravada em `catalogo_meta` e no `indice.binarypb`.

#### Scenario: Indexação de busca e chaves primárias
- **WHEN** as tabelas do catálogo são criadas a partir do DDL gerado pelo `aresta_api`
- **THEN** a tabela `catalogo_croquis` possui chave primária em `croqui_uid`, a tabela `catalogo_aresta` possui chave primária em `uid` e índices em `croqui_uid`, `nome COLLATE NOCASE` e `tipo`, `catalogo_nos_estrada` possui chave primária em `no_osm_id`, `catalogo_distancias_estrada` possui chave primária composta clusterizada `(croqui_uid, no_osm_id) WITHOUT ROWID` (sem índice secundário em `no_osm_id`), e `catalogo_meta` possui chave primária em `chave`.

#### Scenario: Migração automática in-place de catalogo_distancias_estrada para WITHOUT ROWID
- **WHEN** `inicializar_banco_catalogo` abre um arquivo `catalogo.db` pré-existente cuja tabela `catalogo_distancias_estrada` foi criada sem `WITHOUT ROWID` ou que ainda contém o índice legado `idx_catalogo_distancias_estrada_no`
- **THEN** o inicializador preserva integralmente as linhas existentes de `catalogo_distancias_estrada`, recria a tabela com `WITHOUT ROWID`, remove o índice legado `idx_catalogo_distancias_estrada_no` e executa `VACUUM` para compactar o arquivo SQLite.

#### Scenario: Determinismo do hash lógico da versão
- **WHEN** o catálogo contém exatamente os mesmos registros de croquis, entidades e malha rodoviária em duas execuções distintas (seja compilação integral ou incremental)
- **THEN** o hash `versao_catalogo` calculado sobre as linhas ordenadas é estritamente idêntico.
