# Design

## Context

Veja `proposal.md` para a motivação. Atualmente `catalogo_aresta` armazena apenas vias (`uid, croqui_uid, nome, grau, tipo, setor_nome, setor_uid`), omitindo `grupo_uid` e repetindo `setor_nome` em cada via. Além disso, `Grupo`, `Setor` e `Botao` possuem `uid` de 14 caracteres no `croqui.proto`, mas não possuem linhas próprias em `catalogo_aresta`.

## Goals / Non-Goals

**Goals:**
- Normalizar `catalogo_aresta` para que cada entidade com `uid` (`escalada`, `setor`, `grupo`, `botao`) seja uma linha própria identificada por `uid` e discriminada por `tipo`.
- Referenciar apenas `setor_uid` e `grupo_uid` (sem repetir `setor_nome` nem `grupo_nome`), permitindo resolução por `LEFT JOIN` em $O(1)$ via chave primária.
- Padronizar `escalada_tipo` usando `'multienfiada'` para vias de múltiplas enfiadas.
- Garantir que o sincronizador do Cloudflare D1 (`serving/sincronizar_d1_lib.py`) detecte automaticamente se o schema remoto de `catalogo_aresta` precisa ser recriado (ex: migração da estrutura antiga para a nova) durante o bootstrap.

**Non-Goals:**
- Alterar o contrato de cache ou de rotas do Cloudflare Worker em `catalogo.arestaclimb.com/sync` (o algoritmo de Delta Squash já opera de forma genérica pelo campo `uid` de cada registro de `catalogo_aresta`).

## Decisions

### 1. Schema Unificado Normalizado para `catalogo_aresta`
```sql
CREATE TABLE IF NOT EXISTS catalogo_aresta (
    uid TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    croqui_uid TEXT NOT NULL,
    nome TEXT NOT NULL,
    escalada_grau TEXT,
    escalada_tipo TEXT,
    setor_uid TEXT,
    grupo_uid TEXT
);
```
- **Regras de preenchimento por `tipo`:**
  1. `tipo = 'grupo'`: `uid, tipo='grupo', croqui_uid, nome` (`escalada_grau=None, escalada_tipo=None, setor_uid=None, grupo_uid=None`)
  2. `tipo = 'setor'`: `uid, tipo='setor', croqui_uid, nome, grupo_uid` (onde `grupo_uid` é preenchido se o setor pertencer a um grupo, ou `None` caso contrário; demais campos `None`)
  3. `tipo = 'escalada'`: `uid, tipo='escalada', croqui_uid, nome, escalada_grau, escalada_tipo, setor_uid, grupo_uid`
  4. `tipo = 'botao'`: `uid, tipo='botao', croqui_uid, nome` (onde `nome` recebe `botao.texto`; demais campos `None`)
- **Racional:** Uma única coluna `nome` permite que um único índice `idx_catalogo_aresta_nome ON catalogo_aresta(nome COLLATE NOCASE)` atenda buscas textuais por vias, setores e grupos simultaneamente, enquanto `LEFT JOIN catalogo_aresta s ON s.uid = e.setor_uid` e `LEFT JOIN catalogo_aresta g ON g.uid = e.grupo_uid` recuperam os nomes de setor e grupo instantaneamente quando exibidos na UI.

### 2. Migração Automática de Schema no Bootstrap do D1 e SQLite Local
- No `inicializar_banco_catalogo` (local) e `inicializar_schema_d1` (Cloudflare D1), verificamos via `PRAGMA table_info(catalogo_aresta)` se a coluna `escalada_tipo` já existe na tabela `catalogo_aresta`.
- Caso a tabela exista com o formato antigo (sem `escalada_tipo`), executamos `DROP TABLE catalogo_aresta` (e `DELETE FROM deltas_catalogo` no D1) antes do `CREATE TABLE`, garantindo que tanto o `generated/catalogo.db` local quanto o banco `aresta-catalogo` no Cloudflare D1 migrem de forma 100% automática e limpa sem intervenção manual.

## Risks / Trade-offs

- **[Risk] Banco `catalogo.db` preexistente com schema antigo** → Mitigação: Inspecionar `PRAGMA table_info(catalogo_aresta)` na inicialização; se `escalada_tipo` não estiver presente, recriar a tabela automaticamente.
- **[Risk] Limite de 100 bind parameters na API REST do Cloudflare D1** → Mitigação: Com 8 colunas por linha em `catalogo_aresta`, usar `TAMANHO_LOTE_UPSERT_VIAS = 10` (80 parâmetros por query, abaixo do limite de 100 do D1).
