# Design

## Context

Veja `proposal.md` para a motivação completa. Atualmente, `scripts/deploy_generated.py` compila o `catalogo.db` localmente, e o workflow `.github/workflows/deploy.yml` invoca `serving/update_serving.py` para enviar os artefatos ao Cloudflare R2. Precisamos conectar esse pipeline ao Cloudflare D1 e disponibilizar o Cloudflare Worker `catalogo.arestaclimb.com` em `../aresta_backend/cloudflare/catalogo`.

## Goals / Non-Goals

**Goals:**
- Garantir que o identificador de versão do catálogo (`versao_catalogo`) seja 100% determinístico a partir dos dados lógicos, rápido (<10 ms) e imune a conflitos de numeração sequencial em PRs concorrentes no Git.
- Acoplar a atualização do Cloudflare D1 ao `serving/update_serving.py` de forma transacional (D1 antes do R2) usando apenas a biblioteca padrão do Python (`urllib.request`) + `sqlite3`.
- Permitir que a Cloudflare CDN faça cache das respostas de `GET https://catalogo.arestaclimb.com/sync?versao_local=X&versao_destino=Y` na borda externa antes do Worker, zerando invocações de Worker em cache hits.
- Manter apenas `generated/catalogo.db` descomprimido no repositório e no R2.

**Non-Goals:**
- Implementar o cliente Dart/Flutter (`aresta_app`), que será tratado em mudança própria no repositório do aplicativo.
- Usar ferramentas Node.js/Wrangler dentro do runner Python do `aresta_db`.

## Decisions

### 1. Hash Lógico Determinístico (`versao_catalogo`) em vez de SHA-256 físico ou ID sequencial no Git
- **Decisão**: Calcular `sha256` (primeiros 16 caracteres hexadecimais) iterando sobre as tuplas ordenadas de `catalogo_croquis` (`ORDER BY croqui_uid`) e `catalogo_aresta` (`ORDER BY uid`). O resultado é salvo na tabela `catalogo_meta (chave, valor)` dentro do `catalogo.db` e no campo `string versao_catalogo = 3` do `Indice` (`aresta_api/proto/indice.proto`).
- **Racional**:
  1. Os bytes físicos de um arquivo SQLite mudam após operações `DELETE`/`INSERT` incrementais (páginas livres na B-Tree e contador de mudanças no cabeçalho), tornando o SHA-256 do arquivo `.db` inconsistente entre rebuilds totais e parciais.
  2. Um contador inteiro sequencial salvo no Git causaria conflitos constantes entre Pull Requests paralelos.
  3. Como `croqui_uid` e `uid` são `PRIMARY KEY`, o `ORDER BY` percorre o índice primário sem ordenação em memória, levando ~7,8 ms para 4.300 vias.
  4. O `id INTEGER PRIMARY KEY AUTOINCREMENT` existe exclusivamente dentro da tabela `deltas_catalogo` do Cloudflare D1, mapeado para `versao_hash TEXT UNIQUE`.

### 2. Apenas `catalogo.db` Descomprimido
- **Decisão**: Remover a geração de `catalogo.db.gz` de `gerar_catalogo_sqlite_lib.py` e `deploy_generated.py`.
- **Racional**:
  - Acelera a execução de `deploy_generated.py` (especialmente com `--target`), pois o SQLite edita o arquivo in-place sem recomprimir.
  - Pacotes móveis (APK/IPA) já comprimem os assets nativamente.
  - No R2/CDN, a Cloudflare comprime a transferência de `catalogo.db` automaticamente na borda via *Compression Rules*.

### 3. Sincronização D1 via API REST antes do Upload R2 (`serving/sincronizar_d1_lib.py`)
- **Decisão**: No `serving/update_serving.py`, quando o catálogo precisa ser atualizado:
  1. Consulta no D1 o último `versao_hash` registrado em `deltas_catalogo`. Se já for igual ao `versao_catalogo` do `generated/catalogo.db` local, nada precisa ser feito no D1.
  2. Caso contrário, baixa o `catalogo.db` atualmente publicado no R2 para um arquivo temporário antes de sobrescrevê-lo.
  3. Verifica se o `catalogo.db` baixado do R2 corresponde ao estado do D1. Se o D1 estiver vazio (1º deploy) ou dessincronizado, executa bootstrap completo das tabelas `catalogo_croquis` e `catalogo_aresta` em lotes SQL parametrizados e insere a versão inicial em `deltas_catalogo`.
  4. Se o R2 e o D1 estiverem alinhados, usa `gerar_deltas_catalogo.py` (`ATTACH DATABASE` + `EXCEPT`, ~15 ms) para extrair apenas os `upserts` e `deletes` e os envia à API REST do D1 (`POST /client/v4/accounts/{account_id}/d1/database/{database_id}/query`), gravando a nova linha em `deltas_catalogo`.
  5. Somente após o sucesso no D1, faz o upload dos arquivos para o R2 e executa o purge da CDN (incluindo `catalogo.db`).

### 4. Cache na CDN Fora do Worker (`../aresta_backend/cloudflare/catalogo`)
- **Decisão**: O Worker `catalogo.arestaclimb.com` não utiliza `caches.default` internamente; ele retorna `Cache-Control: public, max-age=31536000, s-maxage=31536000, immutable` para respostas `apply_delta` e `Cache-Control: no-store` para `full_download` ou erros.
- **Racional**: Combinado com a *Cache Rule* da Cloudflare CDN (`Eligible for cache` para `catalogo.arestaclimb.com/sync*`), os *cache hits* são servidos diretamente pela camada de CDN sem sequer invocar o Worker, preservando 100% da cota de execução de Workers e leituras do D1.

## Risks / Trade-offs

- **[Limite de parâmetros por query no Cloudflare D1]** → Mitigação: O Cloudflare D1 possui limite de parâmetros vinculados por statement (~100 variáveis por statement SQL). No bootstrap inicial (4.300+ vias) ou em grandes atualizações, `sincronizar_d1_lib.py` divide os `INSERT OR REPLACE` e `DELETE` em lotes seguros (chunks) enviados em batch para a API REST.
- **[Deploy parcial interrompido por falha de rede]** → Mitigação: Como o D1 é atualizado antes do upload do novo `arquivos_serving.yaml` e `catalogo.db` para o R2, uma eventual falha aborta o script mantendo o estado anterior no R2 para re-execução limpa.

## Migration Plan

1. Configurar os secrets `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_CATALOGO_D1_DATABASE_ID` e `CLOUDFLARE_CATALOGO_D1_API_TOKEN` no GitHub Actions (já realizados pelo mantenedor).
2. Atualizar `indice.proto`, recompilar stubs Protobuf e regerar `generated/catalogo.db`, `generated/indice.binarypb`, `generated/indice.yaml` e `generated/arquivos_serving.yaml` (removendo `generated/catalogo.db.gz`).
3. Implementar e publicar o Worker em `../aresta_backend/cloudflare/catalogo`.
4. No primeiro push para a `main`, o `update_serving.py` detectará a tabela `deltas_catalogo` vazia no D1 e fará automaticamente o bootstrap completo dos 43 croquis e 4.279 vias.
