# Proposal

## Why

Atualmente a tabela `catalogo_aresta` (no `catalogo.db` local e no Cloudflare D1) armazena apenas registros de escaladas e repete a string `setor_nome` em cada uma das milhares de vias (~78 KB de redundância nos 43 croquis atuais), omitindo completamente o `grupo_uid` e deixando entidades endereçáveis por UID (`grupo`, `setor` e `botao`) sem linha própria. Normalizar `catalogo_aresta` para registrar todas as entidades com UID (`escalada`, `setor`, `grupo` e `botao`) referenciando apenas `setor_uid` e `grupo_uid` elimina a repetição de nomes, reduz drasticamente o tamanho dos deltas quando um setor ou grupo é renomeado (1 upsert em vez de dezenas) e permite resolver qualquer QR Code (`aresta.cc/<uid>`) ou busca textual com `LEFT JOIN` por chave primária em tempo constante.

## What Changes

- **BREAKING**: Reestruturar o schema da tabela `catalogo_aresta` em `scripts/gerar_catalogo_sqlite_lib.py` e `serving/sincronizar_d1_lib.py` para o formato polimórfico normalizado por UID:
  - `uid TEXT PRIMARY KEY` (NanoID de 14 caracteres da escalada, setor, grupo ou botão)
  - `tipo TEXT NOT NULL` (`'escalada'`, `'setor'`, `'grupo'` ou `'botao'`)
  - `croqui_uid TEXT NOT NULL`
  - `nome TEXT NOT NULL` (nome da escalada, setor, grupo ou texto do botão)
  - `escalada_grau TEXT` (preenchido apenas quando `tipo = 'escalada'`)
  - `escalada_tipo TEXT` (`'esportiva'`, `'tradicional'`, `'boulder'`, `'multienfiada'` ou `'highline'`, preenchido apenas quando `tipo = 'escalada'`)
  - `setor_uid TEXT` (preenchido apenas quando `tipo = 'escalada'`)
  - `grupo_uid TEXT` (preenchido quando `tipo = 'setor'` ou `tipo = 'escalada'` pertencer a um grupo)
- Renomear o valor da modalidade de múltiplas enfiadas em `formatar_tipo_escalada()` de `'multiplas_enfiadas'` para `'multienfiada'`.
- Atualizar `extrair_dados_croqui_para_catalogo()` em `scripts/gerar_catalogo_sqlite_lib.py` para extrair registros de `grupo`, `setor`, `botao` e `escalada`, sem repetir `setor_nome` nas escaladas.
- Atualizar `calcular_versao_catalogo()`, `scripts/gerar_deltas_catalogo.py` e `serving/sincronizar_d1_lib.py` para considerar as novas colunas de `catalogo_aresta` (`uid, tipo, croqui_uid, nome, escalada_grau, escalada_tipo, setor_uid, grupo_uid`) e recriar a tabela automaticamente no D1 caso o schema antigo seja detectado no bootstrap.
- Atualizar a documentação arquitetural em `docs/catalogo_sqlite_e_delta_sync.md` com o novo schema e exemplos de queries com `LEFT JOIN`.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability -->

### Modified Capabilities
- `catalogo-sqlite-delta-sync`: Atualização do requisito de estrutura e geração da tabela `catalogo_aresta` para incluir registros normalizados de `grupo`, `setor`, `botao` e `escalada` com colunas `tipo`, `escalada_grau`, `escalada_tipo` (`'multienfiada'`), `setor_uid` e `grupo_uid`, eliminando `setor_nome` redundante.

## Impact

- `scripts/gerar_catalogo_sqlite_lib.py` e `scripts/gerar_catalogo_sqlite_lib_test.py`
- `scripts/gerar_deltas_catalogo.py` e `scripts/gerar_deltas_catalogo_test.py`
- `serving/sincronizar_d1_lib.py` e `serving/sincronizar_d1_lib_test.py`
- `generated/catalogo.db`, `generated/indice.binarypb`, `generated/indice.yaml` e `generated/arquivos_serving.yaml`
- `docs/catalogo_sqlite_e_delta_sync.md`
- `../aresta_backend/cloudflare/catalogo/test/worker_test.ts` (atualização dos exemplos de payload nos testes)
