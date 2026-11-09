# Spec Delta

## MODIFIED Requirements

### Requirement: Exportação incremental determinística do catálogo em CSV
O gerador do catálogo SHALL exportar ao lado do arquivo `catalogo.db` cinco arquivos CSV determinísticos em UTF-8 com quebras de linha LF (`catalogo_croquis.csv`, `catalogo_aresta.csv`, `catalogo_nos_estrada.csv`, `catalogo_distancias_estrada.csv` e `catalogo_meta.csv`) espelhando todas as tabelas do banco SQLite, atualizando-os apenas quando houver mudança no conteúdo do catálogo ou quando algum dos arquivos CSV estiver ausente no disco.

#### Scenario: Geração dos três arquivos CSV espelhando as tabelas do catálogo
- **WHEN** `catalogo.db` é gerado pela primeira vez ou sofre alteração em suas tabelas
- **THEN** o sistema grava no mesmo diretório do banco os arquivos `catalogo_croquis.csv` (colunas `croqui_uid,id_slug,nome,cidade,estado` ordenadas por `id_slug, croqui_uid`), `catalogo_aresta.csv` (colunas `uid,tipo,croqui_uid,nome,escalada_grau,escalada_tipo,setor_uid,grupo_uid` ordenadas por `croqui_uid, uid`), `catalogo_nos_estrada.csv` (colunas `no_osm_id,latitude_e7,longitude_e7` ordenadas por `no_osm_id`), `catalogo_distancias_estrada.csv` (colunas `croqui_uid,no_osm_id,distancia_metros,na_borda` ordenadas por `croqui_uid, no_osm_id`) e `catalogo_meta.csv` (colunas `chave,valor` ordenadas por `chave`).

#### Scenario: Short-circuit de escrita CSV quando o catálogo não sofre alteração
- **WHEN** o gerador do catálogo é executado, nenhuma linha das tabelas do catálogo muda e os cinco arquivos CSV já existem no disco
- **THEN** o sistema não reescreve nenhum dos cinco arquivos CSV, preservando seus timestamps de modificação no sistema de arquivos.
