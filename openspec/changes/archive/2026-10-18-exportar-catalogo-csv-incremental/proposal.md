# Proposal

## Why

O arquivo binário `generated/catalogo.db` é opaco para revisão em commits Git (assim como o `compilado.binarypb` seria sem o `compilado.yaml`). Além disso, atualmente toda compilação ou salvamento (`Ctrl+S`) sobrescreve incondicionalmente as linhas do croqui no `catalogo.db` com um novo timestamp `atualizado_em = int(time.time())`, causando diffs binários falsos em `generated/catalogo.db` e em `generated/arquivos_serving.yaml` mesmo quando nenhuma informação lógica do catálogo mudou. Precisamos espelhar as 3 tabelas do `catalogo.db` em arquivos CSV determinísticos (`catalogo_croquis.csv`, `catalogo_aresta.csv` e `catalogo_meta.csv`) com atualização incremental rápida e preservar o `catalogo.db` intocado quando os dados de catálogo não sofrerem alteração.

## What Changes

- **Preservação do `catalogo.db` quando dados lógicos não mudam**: Em `scripts/gerar_catalogo_sqlite_lib.py`, antes de remover e reinserir um croqui em `catalogo_croquis` e `catalogo_aresta`, comparar os dados extraídos do `compilado.binarypb` (`croqui_uid, id_slug, nome, cidade, estado` e as linhas ordenadas de `catalogo_aresta` daquele `croqui_uid`) com o estado atual no banco SQLite. Se nada mudou, pular a escrita daquele croqui (preservando `atualizado_em` e evitando sujar páginas do SQLite). Em compilações completas (`alvos=None`), remover do banco eventuais `croqui_uid` órfãos que não existam mais em `generated/`.
- **Inicialização sem mutação desnecessária**: Em `inicializar_banco_catalogo()`, executar migrações ou `COMANDOS_DDL` com `commit()` apenas quando o banco for novo ou quando tabelas/índices/colunas esperados ainda não existirem.
- **Exportação incremental de 3 arquivos CSV ao lado do `catalogo.db`**: Gerar e manter sincronizados no mesmo diretório do banco (`generated/`):
  - `catalogo_croquis.csv` (`croqui_uid,id_slug,nome,cidade,estado` ordenado por `id_slug, croqui_uid`, omitindo `atualizado_em`).
  - `catalogo_aresta.csv` (`uid,tipo,croqui_uid,nome,escalada_grau,escalada_tipo,setor_uid,grupo_uid` ordenado por `croqui_uid, uid` para agrupar cada croqui em um bloco contíguo no `git diff`).
  - `catalogo_meta.csv` (`chave,valor` ordenado por `chave`).
- **Short-circuit de exportação CSV**: Pular a regeneração dos 3 arquivos CSV (`0 ms`) quando nenhuma linha do catálogo tiver mudado na execução e os 3 arquivos CSV já existirem no disco; caso contrário, exportá-los em memória e gravá-los com `escrever_texto_se_modificado` (UTF-8, LF).

## Capabilities

### New Capabilities

### Modified Capabilities
- `catalogo-sqlite-delta-sync`: Atualiza o requisito de atualização seletiva e incremental de croquis para preservar o banco SQLite intocado quando os dados lógicos do catálogo não mudam, e adiciona o requisito de exportação incremental determinística das 3 tabelas do catálogo em arquivos CSV (`catalogo_croquis.csv`, `catalogo_aresta.csv` e `catalogo_meta.csv`).

## Impact

- `scripts/gerar_catalogo_sqlite_lib.py` e `scripts/gerar_catalogo_sqlite_lib_test.py`.
- Artefatos gerados em `generated/`: `generated/catalogo_croquis.csv`, `generated/catalogo_aresta.csv` e `generated/catalogo_meta.csv` (além de estabilizar `generated/catalogo.db` e `generated/arquivos_serving.yaml` quando não houver alteração de catálogo).
