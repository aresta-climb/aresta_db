# Arquitetura: Catálogo SQLite, Delta Sync e Resolução de Links Sociais (aresta.cc)

Este documento descreve a arquitetura do catálogo relacional SQLite (`catalogo.db`), seu pipeline de geração automatizada no repositório `aresta_db`, a sincronização incremental via Cloudflare D1 e o funcionamento dos links curtos e QR Codes (`https://aresta.cc/<uid>`).

---

## 1. Visão Geral da Arquitetura

O ecossistema Aresta utiliza uma divisão clara de responsabilidades para dados offline e na borda:

```
[ aresta_db ]
   │
   ├─► Compilação dos Croquis Protobuf (compilado.binarypb)
   ├─► Geração do Catálogo SQLite (catalogo.db & catalogo.db.gz)
   └─► Diff SQL de Deltas (gerar_deltas_catalogo.py)
            │
            ▼
   [ Cloudflare D1 ]
      ├─ catalogo_croquis
      ├─ catalogo_aresta
      └─ deltas_catalogo (id AUTOINCREMENT, upserts_json, deletes_json)
            │
            ├──► Endpoint GET /sync?desde=X  ──► [ aresta_app (Flutter) ]
            │                                     Busca textual instantânea offline
            │
            └──► Endpoint GET /:uid          ──► [ Redes Sociais & Navegador ]
                 Landing Page com OpenGraph        WhatsApp, Telegram, Twitter, etc.
```

1. **`catalogo.db`**: Banco SQLite compacto contendo metadados de croquis e escaladas, focado em busca textual ultrarrápida no app e resolução instantânea de entidades.
2. **`indice.binarypb`**: Mantém as informações geográficas completas, caixas delimitadoras de mapas, polígonos e dados ricos para a navegação geoespacial.
3. **`aresta.cc/<uid>`**: Worker Cloudflare no domínio de links curtos que atende tanto requisições de sincronização de dados quanto visualização de prévias sociais sem exigir parsing de Protobuf no edge.

---

## 2. Esquema do Banco SQLite (`catalogo.db`)

O banco é projetado para máxima compacidade e consultas indexadas:

```sql
-- Tabela de croquis/picos (~50 a 100 linhas hoje, < 5 KB total)
CREATE TABLE catalogo_croquis (
    croqui_uid TEXT PRIMARY KEY,   -- NanoID de 14 caracteres Base62
    id_slug TEXT NOT NULL,         -- ex: 'br_mg_ferros_pico_dos_ferros'
    nome TEXT NOT NULL,            -- ex: 'Pico dos Ferros'
    cidade TEXT,                   -- ex: 'Ferros'
    uf TEXT,                       -- ex: 'MG'
    atualizado_em INTEGER NOT NULL -- Timestamp Unix
);

-- Tabela de vias/escaladas (~5.000 a 20.000 linhas, ~250 KB comprimido)
CREATE TABLE catalogo_aresta (
    uid TEXT PRIMARY KEY,          -- NanoID de 14 caracteres Base62 da via
    croqui_uid TEXT NOT NULL,      -- Chave lógica para catalogo_croquis
    nome TEXT NOT NULL,            -- ex: 'Pé na Chapa'
    grau TEXT,                     -- ex: '7a', '6sup', 'V5'
    tipo TEXT,                     -- ex: 'esportiva', 'tradicional', 'boulder'
    setor_nome TEXT,               -- ex: 'Cachoeira'
    setor_uid TEXT                 -- NanoID do setor
);

-- Índices otimizados
CREATE INDEX idx_catalogo_aresta_croqui ON catalogo_aresta(croqui_uid);
CREATE INDEX idx_catalogo_aresta_nome ON catalogo_aresta(nome COLLATE NOCASE);
```

---

## 3. Pipeline de Geração e Deploy (`deploy_generated.py`)

A geração do catálogo ocorre no **Passo E** do script de deploy (`scripts/deploy_generated.py`), antes da criação do manifesto final:

1. **Compilação dos Croquis (Passo A)**: Produz os arquivos `compilado.binarypb`.
2. **Cálculo de Checksums e Índice (Passos B e C)**: Gera `indice.binarypb` e `indice.yaml`.
3. **Geração do Catálogo SQLite (Passo E)**:
   - Invoca `scripts.gerar_catalogo_sqlite_lib.gerar_catalogo_completo`.
   - Lê os arquivos `compilado.binarypb` e preenche `catalogo_croquis` e `catalogo_aresta`.
   - Gera a versão compactada `generated/catalogo.db.gz`.
   - **Deploy Parcial**: Caso alvos específicos sejam passados via `--target`, substitui atomicamente apenas os registros dos croquis modificados (`DELETE WHERE croqui_uid = ?` seguido de `INSERT`), preservando os demais.
4. **Manifesto de Serving (Passo D)**:
   - Adiciona `catalogo.db` e `catalogo.db.gz` com seus respectivos hashes SHA-256 em `generated/arquivos_serving.yaml`.

---

## 4. Extração de Deltas para o Cloudflare D1 (`gerar_deltas_catalogo.py`)

No pipeline de CI/CD, antes de publicar uma nova versão:

```bash
python scripts/gerar_deltas_catalogo.py \
  --anterior versao_anterior/catalogo.db \
  --novo generated/catalogo.db \
  --saida deltas.json \
  --sql inserir_delta.sql
```

O script utiliza operações de conjunto nativas do SQLite conectando ambos os bancos via `ATTACH DATABASE`:

- **Upserts**: `SELECT ... FROM novo EXCEPT SELECT ... FROM anterior;`
- **Deletes**: `SELECT ... FROM anterior EXCEPT SELECT ... FROM novo;`

O comando SQL resultante insere o changeset diretamente na tabela `deltas_catalogo` do Cloudflare D1:

```sql
INSERT INTO deltas_catalogo (criado_em, upserts_json, deletes_json)
VALUES (datetime('now'), '{"croquis": [...], "vias": [...]}', '{"croquis": [...], "deletes": [...]}');
```

---

## 5. Contrato do Cloudflare Worker (`aresta.cc`)

### 5.1. Endpoint de Sincronização (`GET /sync?desde=X`)

Utilizado pelo aplicativo móvel para se manter atualizado:

- **Requisição**: `GET https://api.aresta.cc/sync?desde=118`
- **Operação no Edge**:
  1. Consulta no D1:
     ```sql
     SELECT id, upserts_json, deletes_json
     FROM deltas_catalogo
     WHERE id > ?
     ORDER BY id ASC;
     ```
  2. **Delta Squash**: O Worker condensa as alterações por chave primária (`uid` / `croqui_uid`). Se uma via foi alterada múltiplas vezes ao longo de 50 versões, apenas o estado final mais recente é transmitido.
- **Resposta**:
  ```json
  {
    "versao_atual": 120,
    "total_deltas": 2,
    "upserts": {
      "croquis": [...],
      "vias": [...]
    },
    "deletes": {
      "croquis": [],
      "vias": ["viaAntiga1234"]
    }
  }
  ```
- **Aplicação no Cliente**: O aplicativo móvel executa os `deletes` e `upserts` dentro de uma única transação SQLite local e avança seu ponteiro de versão local para 120.

---

### 5.2. Resolução de Links Sociais e QR Codes (`GET /:uid`)

Ao compartilhar uma via ou setor nas redes sociais (WhatsApp, Instagram, Twitter, iMessage, etc.):

- **Consulta no D1**:
  ```sql
  SELECT 
      v.nome AS via_nome, v.grau, v.tipo, v.setor_nome,
      c.nome AS croqui_nome, c.cidade, c.uf, c.id_slug
  FROM catalogo_aresta v
  LEFT JOIN catalogo_croquis c ON v.croqui_uid = c.croqui_uid
  WHERE v.uid = ?;
  ```
- **HTML Retornado (~3 KB)**:
  ```html
  <!DOCTYPE html>
  <html lang="pt-BR">
  <head>
    <meta charset="utf-8">
    <title>Pé na Chapa (7a) - Pico dos Ferros | Aresta</title>
    <meta property="og:title" content="Pé na Chapa (7a) • Pico dos Ferros">
    <meta property="og:description" content="Setor Cachoeira, Ferros - MG. Acesse fotos, betas e mapas no app Aresta.">
    <meta property="og:image" content="https://cdn.aresta.cc/thumbnails/br_mg_ferros.webp">
    <meta name="twitter:card" content="summary_large_image">
    <script>
      // Universal Link / App Link para abrir direto no aplicativo
      window.location.href = "aresta://v/viaReal1234567";
    </script>
  </head>
  <body>
    <div class="card">
      <h1>Pé na Chapa <span>7a</span></h1>
      <p>Setor Cachoeira • Pico dos Ferros, MG</p>
      <a href="https://play.google.com/store/apps/details?id=cc.aresta" class="btn">Baixar na Google Play</a>
      <a href="https://apps.apple.com/app/aresta/id000000000" class="btn">Baixar na App Store</a>
    </div>
  </body>
  </html>
  ```
- **Cache CDN**: Cabeçalho `Cache-Control: public, max-age=86400, stale-while-revalidate=604800`. O Worker roda uma única vez por via; as consultas subsequentes são entregues pela CDN em ~15ms.

---

## 6. Mecanismo de Purge Global de Emergência (Kill Switch)

Para garantir recuperação instantânea caso uma inconsistência de dados ou corrupção de banco ocorra nos clientes móveis, adotamos um mecanismo acionado via **Firebase Remote Config**:

### 6.1. Linha de Base no Build (`timestampBuildCatalogo`)

Cada build do aplicativo móvel (`aresta_app`) embute em código uma constante com o timestamp do momento de empacotamento:

```dart
const int timestampBuildCatalogo = 1728650000;
```

### 6.2. Fluxo na Primeira Instalação (Zero Consumo de Rede)

1. O app desempacota o `catalogo.db` dos assets locais para a pasta de dados.
2. Inicializa a preferência:
   ```dart
   local.ultimo_purge_executado = max(timestampBuildCatalogo, firebase.catalogo_purge_timestamp);
   ```
3. Qualquer purge configurado no Firebase no passado (antes da compilação do release) é **automaticamente ignorado**, garantindo que o usuário recém-instalado não gaste dados móveis à toa.

### 6.3. Disparo de Emergência

Caso seja necessário forçar a reinicialização de todos os aplicativos ativos:

1. O mantenedor altera a variável `catalogo_purge_timestamp` no Firebase Console para o timestamp atual (ex: `1728700000`).
2. Na próxima abertura do app:
   ```dart
   final int ultimoExecutado = prefs.getInt('ultimo_purge_catalogo') ?? timestampBuildCatalogo;
   final int purgeRemoto = remoteConfig.getInt('catalogo_purge_timestamp');

   if (purgeRemoto > ultimoExecutado) {
     // Descarta o SQLite local e zera o ponteiro de versão
     await descartarCatalogoLocal();
     // Efetua download limpo do catalogo.db.gz integral do CDN
     await baixarEDescompactarCatalogoGzip();
     // Salva a nova marca d'água
     await prefs.setInt('ultimo_purge_catalogo', purgeRemoto);
   }
   ```
