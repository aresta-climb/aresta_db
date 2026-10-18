# Design

## Context

Consulte `proposal.md` para a motivação e `specs/catalogo-sqlite-delta-sync/spec.md` para os requisitos comportamentais.
Hoje, `scripts/gerar_catalogo_sqlite_lib.py` executa `remover_croqui_do_catalogo()` seguido de `inserir_croqui_no_catalogo()` para todo croqui alvo, gravando sempre um novo `atualizado_em = int(time.time())`. Isso altera as páginas binárias do SQLite em qualquer `Ctrl+S` do Aresta Editor, mesmo quando apenas geometrias de mapa ou textos Markdown foram editados. Além disso, não há representação textual das três tabelas do `catalogo.db` para inspeção humana em `git diff`.

## Goals / Non-Goals

**Goals:**
- Garantir que `generated/catalogo.db` tenha zero bytes modificados quando os metadados de catálogo dos croquis compilados não mudarem.
- Manter três arquivos CSV globais (`catalogo_croquis.csv`, `catalogo_aresta.csv` e `catalogo_meta.csv`) ao lado do `catalogo.db` com custo de `0 ms` quando o catálogo não muda e `~2 ms` quando muda.
- Agrupar as linhas de um mesmo croqui de forma contígua em `catalogo_aresta.csv` para produzir blocos coesos no `git diff`.

**Non-Goals:**
- Alterar o esquema SQL canônico definido em `aresta_api/sql/catalogo.sql`.
- Incluir os arquivos `.csv` de debug no manifesto de CDN (`arquivos_serving.yaml`) consumido pelo aplicativo móvel.

## Decisions

1. **Três arquivos CSV globais na raiz de `generated/` vs. CSV particionado por pasta de croqui**
   - *Decisão*: Gerar `catalogo_croquis.csv`, `catalogo_aresta.csv` e `catalogo_meta.csv` no mesmo diretório de `catalogo.db` (`generated/`).
   - *Racional*: Mantém fidelidade 1:1 com o banco SQLite único usado em produção (`catalogo.db`), permitindo inspecionar em um só lugar exatamente o que está nas três tabelas do banco. O custo de escrita é mitigado pelo short-circuit quando não há alteração lógica.

2. **Detecção de mudança por croqui antes de mutar o SQLite (`_croqui_modificado_no_catalogo`)**
   - *Decisão*: Antes de executar `DELETE` e `INSERT` para um `croqui_uid`, consultar no SQLite a tupla `(croqui_uid, id_slug, nome, cidade, estado)` em `catalogo_croquis` e a lista ordenada por `uid` de `(uid, tipo, croqui_uid, nome, escalada_grau, escalada_tipo, setor_uid, grupo_uid)` em `catalogo_aresta` (usando o índice existente `idx_catalogo_aresta_croqui`). Só executar `DELETE` + `INSERT` se houver diferença.
   - *Racional*: Evita sujar páginas do SQLite e preserva `atualizado_em` intocado quando uma recompilação não altera nenhum dado indexado pelo catálogo.

3. **Omissão de `atualizado_em` em `catalogo_croquis.csv` e ordenação contígua por croqui em `catalogo_aresta.csv`**
   - *Decisão*:
     - `catalogo_croquis.csv` exporta `croqui_uid,id_slug,nome,cidade,estado` com `ORDER BY id_slug, croqui_uid` (mesmas colunas usadas no hash `calcular_versao_catalogo`).
     - `catalogo_aresta.csv` exporta `uid,tipo,croqui_uid,nome,escalada_grau,escalada_tipo,setor_uid,grupo_uid` com `ORDER BY croqui_uid, uid`.
     - `catalogo_meta.csv` exporta `chave,valor` com `ORDER BY chave`.
     - Valores `None` (`NULL` no SQLite) são serializados como string vazia `""` no CSV padrão RFC 4180 com terminador `\n` (LF).
   - *Racional*: Ordenar `catalogo_aresta.csv` por `(croqui_uid, uid)` garante que todas as vias, setores, grupos e botões de um mesmo croqui fiquem juntos em um único bloco contíguo no arquivo CSV, evitando dezenas de hunks espalhados no `git diff`.

## Risks / Trade-offs

- **[Risco] Croqui removido do diretório `generated/` em compilação completa sem `--force`** → *Mitigação*: Quando `alvos is None`, comparar o conjunto de `croqui_uid` presentes nos `compilado.binarypb` encontrados com os `croqui_uid` registrados em `catalogo_croquis`, removendo eventuais órfãos e marcando o banco como modificado.
- **[Risco] Diferença de quebras de linha no Windows (`CRLF` vs `LF`)** → *Mitigação*: Utilizar `lineterminator="\n"` no `csv.writer` e gravar via escrita UTF-8 com LF explícito apenas quando o conteúdo textual mudar.
