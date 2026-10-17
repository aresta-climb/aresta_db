## 1. Normalização do Schema Local e Extração Unificada (`scripts/gerar_catalogo_sqlite_lib.py` e `scripts/gerar_deltas_catalogo.py`)

- [x] 1.1 Escrever testes em `scripts/gerar_catalogo_sqlite_lib_test.py` (Red) para validar o novo schema da tabela `catalogo_aresta` (`uid`, `tipo`, `croqui_uid`, `nome`, `escalada_grau`, `escalada_tipo`, `setor_uid`, `grupo_uid`), a indexação unificada de grupos (`tipo='grupo'`), setores (`tipo='setor'`), botões (`tipo='botao'`) e escaladas (`tipo='escalada'`), o mapeamento de modalidades (`esportiva`, `tradicional`, `boulder`, `multienfiada`, `highline`), a migração automática da tabela legada quando `escalada_tipo` não existir, e a resolução de nomes de setor e grupo via `LEFT JOIN`.
- [x] 1.2 Atualizar `scripts/gerar_catalogo_sqlite_lib.py` e `scripts/gerar_deltas_catalogo.py` (Green/Refactor) com extração de grupos, setores, botões e escaladas a partir do `Croqui`, detecção e recriação automática da tabela `catalogo_aresta` legada em `inicializar_banco_catalogo` e queries parametrizadas com as 8 colunas do novo schema.
- [x] 1.3 Executar pytest com cobertura para `scripts/gerar_catalogo_sqlite_lib.py` e `scripts/gerar_deltas_catalogo.py` garantindo 100% de cobertura comportamental.

## 2. Sincronização Incremental e Migração no Cloudflare D1 (`serving/sincronizar_d1_lib.py`)

- [x] 2.1 Escrever testes em `serving/sincronizar_d1_lib_test.py` (Red) validando a inicialização/migração automática do schema no D1 (recriação de `catalogo_aresta` e limpeza de `deltas_catalogo` caso `escalada_tipo` não exista), o diff incremental por `uid` para registros de todos os tipos (`escalada`, `setor`, `grupo`, `botao`), e que renomear um setor gera exatamente 1 `upsert_via` sem reescrever as escaladas daquele setor.
- [x] 2.2 Implementar Fake determinístico `serving/cliente_cloudflare_d1_fake.py` com `serving/cliente_cloudflare_d1_fake_test.py` e atualizar `serving/sincronizar_d1_lib.py` e `serving/sincronizar_d1_lib_test.py` (Green/Refactor, eliminando mocks) para suportar a nova estrutura de `catalogo_aresta` nos snapshots, nas tabelas do D1 e nos payloads JSON de deltas.
- [x] 2.3 Executar pytest com cobertura para `serving/sincronizar_d1_lib.py` e `serving/cliente_cloudflare_d1_fake.py` garantindo 100% de cobertura comportamental.

## 3. Cloudflare Worker e Documentação

- [x] 3.1 Atualizar os comentários e documentação em `../aresta_backend/cloudflare/catalogo/src/index.ts` refletindo que `upserts.vias` e `deletes.vias` operam sobre registros unificados de `catalogo_aresta` (`escalada`, `setor`, `grupo`, `botao`) e validar os testes do Worker (`deno test`).
- [x] 3.2 Atualizar a documentação em `README.md` descrevendo o schema normalizado de `catalogo_aresta` e um exemplo de consulta SQL com `LEFT JOIN` para recuperar `setor_nome` e `grupo_nome`.
