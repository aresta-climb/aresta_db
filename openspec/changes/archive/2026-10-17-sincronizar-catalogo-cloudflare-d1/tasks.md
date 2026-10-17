# Tasks

## 1. Hash Lógico Determinístico e Simplificação do Catálogo SQLite

- [x] 1.1 Adicionar o campo `string versao_catalogo = 3;` na mensagem `Indice` em `aresta_api/proto/indice.proto`, executar `python build.py` e verificar que `indice_pb2.py` expõe o campo
- [x] 1.2 Atualizar `scripts/gerar_catalogo_sqlite_lib_test.py` e `scripts/gerar_catalogo_sqlite_lib.py` para criar a tabela `catalogo_meta`, calcular e persistir `versao_catalogo` (SHA-256 curto de 16 caracteres sobre as linhas ordenadas) e remover a geração de `catalogo.db.gz`, garantindo 100% de cobertura unitária
- [x] 1.3 Atualizar `scripts/deploy_generated_test.py` e `scripts/deploy_generated.py` para gravar `versao_catalogo` no `indice.binarypb` e `indice.yaml`, registrar apenas `catalogo.db` em `arquivos_serving.yaml` e remover `generated/catalogo.db.gz`, validando que todos os testes passam
- [x] 1.4 Atualizar `scripts/gerar_deltas_catalogo_test.py` e `scripts/gerar_deltas_catalogo.py` para incluir `versao_hash` da versão destino no changeset JSON e no statement SQL de `deltas_catalogo`, mantendo 100% de cobertura unitária

## 2. Sincronização do Cloudflare D1 no Pipeline de Serving

- [x] 2.1 Criar `serving/sincronizar_d1_lib_test.py` e `serving/sincronizar_d1_lib.py` implementando o cliente REST do Cloudflare D1 (`CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_CATALOGO_D1_DATABASE_ID`, `CLOUDFLARE_CATALOGO_D1_API_TOKEN`), inicialização de schema, diff incremental contra o `catalogo.db` anterior do R2 e fallback de bootstrap completo em lotes, com 100% de cobertura unitária
- [x] 2.2 Atualizar `serving/update_serving.py` e criar/atualizar `serving/update_serving_test.py` para executar a sincronização do D1 antes do upload do novo `catalogo.db` para o R2 e incluir `catalogo.db` no purge de cache da Cloudflare CDN, com 100% de cobertura unitária
- [x] 2.3 Atualizar `.github/workflows/deploy.yml` adicionando os secrets `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_CATALOGO_D1_DATABASE_ID` e `CLOUDFLARE_CATALOGO_D1_API_TOKEN` e incluindo os arquivos necessários no `sparse-checkout`
- [x] 2.4 Atualizar `docs/catalogo_sqlite_e_delta_sync.md` refletindo a URL `https://catalogo.arestaclimb.com/sync?versao_local=...&versao_destino=...`, a remoção de `catalogo.db.gz`, o hash lógico determinístico e a configuração da Cache Rule na Cloudflare CDN

## 3. Cloudflare Worker do Catálogo em `../aresta_backend`

- [x] 3.1 Criar/atualizar a estrutura em `../aresta_backend/cloudflare/catalogo/` (`wrangler.jsonc`, `package.json`, `deno.json`, `README.md`) configurada para o domínio `catalogo.arestaclimb.com` e binding D1 `DB`
- [x] 3.2 Criar a suíte de testes TDD `../aresta_backend/cloudflare/catalogo/test/worker_test.ts` e implementar `../aresta_backend/cloudflare/catalogo/src/index.ts` cobrindo `/health`, `/sync` com Delta Squash, `Cache-Control: public, max-age=31536000, s-maxage=31536000, immutable` e fallback `full_download` (`Cache-Control: no-store`), verificando que `deno test -A` passa com 100% de sucesso
