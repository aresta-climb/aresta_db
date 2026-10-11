# Design: Catálogo SQLite e Sincronização de Deltas

## Context

Atualmente o repositório compila croquis YAML/Markdown para Protobuf (`compilado.binarypb`) e gera o índice global de picos (`indice.binarypb`). Para suportar a resolução instantânea de links curtos e QR Codes (`https://aresta.cc/<uid>`) na borda via Cloudflare Worker/D1 e oferecer busca textual offline ultra-rápida no aplicativo Flutter (`aresta_app`), adotamos um catálogo relacional SQLite (`catalogo.db`) distribuído pelo CDN e mantido sincronizado por deltas.

Ver detalhes de motivação em [proposal.md](file:///c:/Renato/Devel/aresta-climb/aresta_db/openspec/changes/catalogo-sqlite-e-delta-sync/proposal.md).

## Goals / Non-Goals

**Goals:**
- Implementar biblioteca isolada `scripts/gerar_catalogo_sqlite_lib.py` com 100% de cobertura de testes unitários seguindo os princípios de engenharia Aresta.
- Estruturar o banco `catalogo.db` com duas tabelas enxutas: `catalogo_croquis` (~5 KB) e `catalogo_aresta` (~250 KB comprimido).
- Integrar a geração ao final do pipeline de deploy (`deploy_generated.py`) como Passo E, com geração automática de `catalogo.db.gz` e inclusão em `arquivos_serving.yaml`.
- Suportar compilação total e compilação parcial/incremental (`--target`), substituindo apenas os registros dos croquis alterados sem descartar os demais.
- Desenvolver utilitário de diff SQL (`scripts/gerar_deltas_catalogo.py`) que compara duas versões do catálogo usando comandos nativos `EXCEPT` do SQLite e gera o payload para a tabela `deltas_catalogo` no Cloudflare D1.
- Projetar o contrato do Cloudflare Worker para renderização de Landing Page ultra-leve com OpenGraph e Twitter Cards sem dependência de Protobuf.

**Non-Goals:**
- Não haverá visualizador completo de croquis ou mapas na web; links `aresta.cc/<uid>` abrem o aplicativo móvel ou direcionam para as lojas de aplicativos.
- O catálogo SQLite não armazena detalhes vetoriais de mapas, fotos ou polígonos geográficos (que continuam sob responsabilidade do `indice.binarypb` e dos arquivos do croqui).
- Não haverá controle de versão linha por linha no SQLite local do celular; o versionamento é mantido como um único inteiro na tabela de metadados do app (`meta_versao`).

## Decisions

### 1. Duas tabelas normalizadas (`catalogo_croquis` e `catalogo_aresta`)
- **Decisão:** Separar dados gerais do pico/croqui em `catalogo_croquis` e vias em `catalogo_aresta`, usando `croqui_uid` (14 caracteres) como chave de ligação lógica.
- **Rationale:** 
  - Evita duplicar o nome do croqui, cidade e estado em milhares de linhas de escaladas.
  - Permite que o Cloudflare Worker faça um `JOIN` simples de 3ms no D1 para montar o título e descrição das meta tags OpenGraph.
  - Permite resolução direta de QR Codes e links do próprio croqui (`aresta.cc/<croqui_uid>`).
  - No app móvel, permite busca e filtro por localidade sem decodificar o Protobuf.
- **Alternativas consideradas:**
  - *Desnormalizar na tabela de vias:* aumentaria o tamanho em mais de 500 KB desnecessariamente.
  - *Worker decodificar Protobuf:* exigiria dependências pesadas de parsing Protobuf em JavaScript no Worker e download do `indice.binarypb`.

### 2. Esquema do Banco SQLite (`catalogo.db`)

```sql
CREATE TABLE catalogo_croquis (
    croqui_uid TEXT PRIMARY KEY,
    id_slug TEXT NOT NULL,
    nome TEXT NOT NULL,
    cidade TEXT,
    uf TEXT,
    atualizado_em INTEGER NOT NULL
);

CREATE TABLE catalogo_aresta (
    uid TEXT PRIMARY KEY,
    croqui_uid TEXT NOT NULL,
    nome TEXT NOT NULL,
    grau TEXT,
    tipo TEXT,
    setor_nome TEXT,
    setor_uid TEXT
);

CREATE INDEX idx_catalogo_aresta_croqui ON catalogo_aresta(croqui_uid);
CREATE INDEX idx_catalogo_aresta_nome ON catalogo_aresta(nome COLLATE NOCASE);
```

### 3. Mecanismo de Diff SQL para Cloudflare D1
- **Decisão:** Comparar duas instâncias de `catalogo.db` (versão N-1 vs versão N) conectando ambos via `ATTACH DATABASE` e executando queries de conjunto (`EXCEPT`).
- **Rationale:** O SQLite executa a diferença em disco ou memória em dezenas de milissegundos, gerando os conjuntos exatos de `upserts` (novos ou alterados) e `deletes` (removidos) sem consumir memória RAM do processo Python.
- **Alternativas consideradas:**
  - *Diffing em Python:* mais propenso a inconsistências e consome mais memória ao carregar milhares de registros.

### 4. Estrutura de Deltas no Cloudflare D1 e Endpoint `/sync`
- **Decisão:** Tabela no D1:
  ```sql
  CREATE TABLE deltas_catalogo (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      criado_em TEXT NOT NULL,
      upserts_json TEXT NOT NULL,
      deletes_json TEXT NOT NULL
  );
  ```
- **Rationale:** O app Flutter envia `GET /sync?desde=118`. O Worker consulta `SELECT id, upserts_json, deletes_json FROM deltas_catalogo WHERE id > 118 ORDER BY id ASC`, faz o squash (se um item foi alterado várias vezes, envia só a versão final) e retorna:
  ```json
  {
      "versao_atual": 120,
      "upserts": [...],
      "deletes": [...]
  }
  ```
  O app aplica as mudanças dentro de uma transação SQLite local e salva `versao_atual = 120`.

### 5. Landing Page Social na Borda (`aresta.cc/<uid>`)
- **Decisão:** Cloudflare Worker renderiza HTML de ~3 KB contendo tags `<meta property="og:title" ...>`, `<meta property="og:description" ...>`, script de redirecionamento `aresta://v/<uid>` e botões de download nas lojas.
- **Cache CDN:** Cabeçalho `Cache-Control: public, max-age=86400, stale-while-revalidate=604800`.
- **Rationale:** Garante que o Worker execute a query no D1 apenas na primeira requisição; acessos subsequentes de compartilhamento em redes sociais são atendidos pelo cache de borda em ~15ms.

## Risks / Trade-offs

- **[Deploy parcial com alvos incompletos]** → Mitigação: Em deploys parciais (`--target`), o script carrega o `catalogo.db` pré-existente da pasta `generated/`, remove apenas os croquis correspondentes (`DELETE WHERE croqui_uid IN (...)`) e insere os novos dados compilados. Caso o banco não exista, ele é criado do zero com os alvos fornecidos.
- **[Conflito de schema ou versões antigas do app]** → Mitigação: O schema é fixo e minimalista. Se um app estiver desatualizado há muito tempo (>100 versões de delta), o Worker pode instruí-lo a baixar diretamente o arquivo integral `catalogo.db.gz`.

## Migration Plan

1. A geração do catálogo é puramente aditiva e não interfere nos arquivos `compilado.binarypb` ou `indice.binarypb`.
2. Em caso de falha no passo do catálogo durante o deploy, os artefatos existentes de índice permanecem válidos.
