# Proposal

## Why

O arquivo `catalogo.db` já é gerado no pipeline local e enviado ao Cloudflare R2, porém o banco relacional de borda Cloudflare D1 ainda não é atualizado automaticamente pelo deploy no GitHub Actions (`serving/update_serving.py`) e o Worker de borda (`catalogo.arestaclimb.com`) precisa ser implementado em `../aresta_backend/cloudflare/catalogo`. Além disso, para garantir que o endpoint `/sync` seja 100% cacheável na CDN sem invocar o Worker em cache hits e sem sofrer com não-determinismo binário do SQLite ou conflitos de merge em PRs no Git, precisamos adotar um hash lógico determinístico das linhas do catálogo (`versao_catalogo`) e manter apenas o `catalogo.db` descomprimido.

## What Changes

- **Hash Lógico Determinístico (`versao_catalogo`)**: Cálculo do SHA-256 curto (16 hex chars) sobre o conteúdo ordenado de `catalogo_croquis` e `catalogo_aresta`, gravado na tabela `catalogo_meta` do `catalogo.db` e no campo `string versao_catalogo = 3` da mensagem `Indice` (`aresta_api/proto/indice.proto`).
- **Remoção de `catalogo.db.gz`**: Eliminação da compressão gzip local em `gerar_catalogo_sqlite_lib.py` e `deploy_generated.py`, mantendo apenas `generated/catalogo.db` descomprimido para máxima velocidade de atualização incremental e delegando a compressão de tráfego à Cloudflare CDN.
- **Sincronização Automática com Cloudflare D1 no Deploy (`serving/sincronizar_d1_lib.py` e `serving/update_serving.py`)**:
  - Comunicação via API REST oficial do Cloudflare D1 usando `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_CATALOGO_D1_DATABASE_ID` e `CLOUDFLARE_CATALOGO_D1_API_TOKEN`.
  - Ordem transacional segura no `update_serving.py`: baixa o `catalogo.db` anterior do R2 para diretório temporário, calcula o diff via `EXCEPT` contra o `generated/catalogo.db` local, aplica os `upserts` e `deletes` nas tabelas `catalogo_croquis` e `catalogo_aresta` do D1, registra a nova versão em `deltas_catalogo` (com `versao_hash`) e somente após o sucesso no D1 substitui o `catalogo.db` no R2 e purga o cache da CDN.
  - Fallback automático de bootstrap completo caso o D1 esteja vazio ou dessincronizado.
- **Cloudflare Worker do Catálogo (`../aresta_backend/cloudflare/catalogo`)**:
  - Implementação do Worker em TypeScript com suporte a `GET /health` e `GET /sync?versao_local=<hash_local>&versao_destino=<hash_destino>` sob o domínio `catalogo.arestaclimb.com`.
  - Delta Squash em memória e cabeçalho `Cache-Control: public, max-age=31536000, s-maxage=31536000, immutable` para cache completo na CDN Cloudflare antes do Worker (zero consumo de cota de Worker em cache hits).
  - Fallback `{"acao": "full_download"}` com `Cache-Control: no-store` quando `versao_local` não for encontrada no histórico do D1.

## Capabilities

### New Capabilities

<!-- Nenhuma nova capability isolada; estende catalogo-sqlite-delta-sync -->

### Modified Capabilities

- `catalogo-sqlite-delta-sync`: Atualiza requisitos de compressão (apenas `catalogo.db` descomprimido), introduz o versionamento por hash lógico determinístico (`versao_catalogo` em `catalogo_meta` e `indice.proto`), especifica a sincronização transacional com o Cloudflare D1 no deploy (`update_serving.py`) e define o contrato cacheável do Worker `catalogo.arestaclimb.com/sync`.

## Impact

- `aresta_api/proto/indice.proto` e stubs compilados (`indice_pb2.py`).
- `scripts/gerar_catalogo_sqlite_lib.py`, `scripts/gerar_deltas_catalogo.py` e `scripts/deploy_generated.py`.
- `serving/sincronizar_d1_lib.py`, `serving/update_serving.py` e `.github/workflows/deploy.yml`.
- `docs/catalogo_sqlite_e_delta_sync.md`.
- Repositório irmão `../aresta_backend/cloudflare/catalogo/` (`wrangler.jsonc`, `src/index.ts`, `test/worker_test.ts`, `README.md`).
