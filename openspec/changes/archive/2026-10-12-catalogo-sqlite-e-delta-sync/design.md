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
- Estabelecer mecanismo de recuperação de desastres e purge global do catálogo via Firebase Remote Config com proteção de linha de base (baseline) no build para novas instalações.

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

### 4. Estrutura de Deltas no Cloudflare D1 e Retenção Contínua
- **Decisão:** Tabela no D1:
  ```sql
  CREATE TABLE deltas_catalogo (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      criado_em TEXT NOT NULL,
      upserts_json TEXT NOT NULL,
      deletes_json TEXT NOT NULL
  );
  ```
- **Retenção e Desempenho:**
  - O Cloudflare D1 não possui limite artificial no número de deltas mantidos. Consultas `WHERE id > :desde ORDER BY id ASC` usam a chave primária indexada (B-Tree), respondendo em 2 a 5ms mesmo com milhares de registros.
  - **Delta Squash (Agregação no Edge):** O Worker consulta todos os deltas do intervalo requisitado e consolida as entidades por chave primária (`uid`). Se uma via foi alterada múltiplas vezes ao longo de 50 versões, o Worker envia apenas o estado final mais recente (1 único `upsert`).
  - O app Flutter aplica os `upserts` e `deletes` condensados dentro de uma única transação SQLite local e avança seu ponteiro de versão local para a `versao_atual`.

### 5. Mecanismo de Purge Global de Emergência (Firebase Remote Config)
- **Decisão:** Implementar um "Kill Switch" de recuperação de emergência para casos em que o catálogo local de um cliente fique corrompido ou inconsistente.
- **Configuração Remota:**
  - Chave no Firebase Remote Config: `catalogo_purge_timestamp` (inteiro Unix timestamp).
  - No build do app (`aresta_app`): embutida constante `timestampBuildCatalogo` representando o momento da geração dos assets do release.
- **Lógica de Execução no App:**
  ```dart
  final int ultimoExecutado = prefs.getInt('ultimo_purge_catalogo') ?? timestampBuildCatalogo;
  final int purgeRemoto = remoteConfig.getInt('catalogo_purge_timestamp');

  if (purgeRemoto > ultimoExecutado) {
    await executarPurgeERebuildCatalogo(); // Deleta catalogo.db local e baixa catalogo.db.gz limpo
    await prefs.setInt('ultimo_purge_catalogo', purgeRemoto);
  }
  ```
- **Garantias Operacionais:**
  1. *Primeira Instalação:* O app desempacota o `catalogo.db` dos assets pré-embarcados. Como qualquer purge emitido no passado é menor ou igual ao `timestampBuildCatalogo`, purges históricos são ignorados e nenhum download é disparado.
  2. *Disparo em Emergência:* Ao alterar o timestamp no Firebase Console para o momento presente, o valor supera o `ultimoExecutado` de todos os aplicativos ativos no mundo, forçando o descarte e o download limpo do `catalogo.db.gz` na próxima abertura.

### 6. Landing Page Social na Borda (`aresta.cc/<uid>`)
- **Decisão:** Cloudflare Worker renderiza HTML de ~3 KB contendo tags `<meta property="og:title" ...>`, `<meta property="og:description" ...>`, script de redirecionamento `aresta://v/<uid>` e botões de download nas lojas.
- **Cache CDN:** Cabeçalho `Cache-Control: public, max-age=86400, stale-while-revalidate=604800`.
- **Rationale:** Garante que o Worker execute a query no D1 apenas na primeira requisição; acessos subsequentes de compartilhamento em redes sociais são atendidos pelo cache de borda em ~15ms.

## Risks / Trade-offs

- **[Deploy parcial com alvos incompletos]** → Mitigação: Em deploys parciais (`--target`), o script carrega o `catalogo.db` pré-existente da pasta `generated/`, remove apenas os croquis correspondentes (`DELETE WHERE croqui_uid IN (...)`) e insere os novos dados compilados. Caso o banco não exista, ele é criado do zero com os alvos fornecidos.
- **[Tamanho de delta acumulado muito grande]** → Mitigação: Caso a soma de deltas de um intervalo longo seja superior ao tamanho do banco compactado (~250 KB), o Worker pode opcionalmente sinalizar para o cliente efetuar o download direto de `catalogo.db.gz`, economizando banda.

## Migration Plan

1. A geração do catálogo é puramente aditiva e não interfere nos arquivos `compilado.binarypb` ou `indice.binarypb`.
2. Em caso de falha no passo do catálogo durante o deploy, os artefatos existentes de índice permanecem válidos.
