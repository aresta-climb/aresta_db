# Arquitetura: Catálogo SQLite, Delta Sync e Sincronização com Cloudflare D1

Este documento descreve a arquitetura do catálogo relacional SQLite (`catalogo.db`), seu pipeline de geração automatizada no repositório `aresta_db`, o versionamento por hash lógico determinístico (`versao_catalogo`) e a sincronização incremental via Cloudflare D1 e Cloudflare CDN (`catalogo.arestaclimb.com`).

---

## 1. Visão Geral da Arquitetura

O ecossistema Aresta utiliza uma divisão clara de responsabilidades para dados offline e na borda:

```
[ aresta_db (deploy_generated.py) ]
   │
   ├─► Compilação dos Croquis Protobuf (compilado.binarypb)
   ├─► Geração do Catálogo SQLite descomprimido (generated/catalogo.db)
   └─► Hash Lógico Determinístico (versao_catalogo em catalogo_meta e indice.binarypb)
            │
            ▼
[ Deploy CI/CD (serving/update_serving.py) ]
   │
   ├─► 1. Baixa catalogo.db anterior do R2 e calcula diff SQL (gerar_deltas_catalogo.py)
   ├─► 2. Aplica upserts/deletes e grava delta em deltas_catalogo no Cloudflare D1 (API REST)
   └─► 3. Só após sucesso no D1, faz upload para o R2 e purga cache da CDN
            │
            ▼
   [ Cloudflare D1 + Worker (catalogo.arestaclimb.com) ]
      ├─ catalogo_croquis
      ├─ catalogo_aresta
      └─ deltas_catalogo (id AUTOINCREMENT, versao_hash UNIQUE, upserts_json, deletes_json)
            │
            └──► GET /sync?versao_local=A&versao_destino=B ──► [ aresta_app (Flutter) ]
                 (Cacheado na borda da CDN com immutable)       Busca textual instantânea offline
```

1. **`catalogo.db`**: Banco SQLite descomprimido contendo metadados de croquis e escaladas, focado em busca textual ultrarrápida no app. Não geramos `catalogo.db.gz` localmente para manter o `deploy_generated.py` instantâneo; a compressão de rede é realizada automaticamente na borda pela CDN da Cloudflare e nativamente pelos pacotes APK/IPA.
2. **`indice.binarypb`**: Mantém as informações geográficas completas e expõe o campo `versao_catalogo` (campo `3` da mensagem `Indice`), permitindo que o aplicativo descubra imediatamente se seu `catalogo.db` local precisa de sincronização.
3. **`catalogo.arestaclimb.com/sync`**: Worker Cloudflare conectado ao banco D1 que condensa deltas entre quaisquer duas versões (`versao_local` e `versao_destino`) e delega o cache de respostas para a CDN da Cloudflare (Cache Rule), evitando invocações repetidas do Worker.

---

## 2. Esquema do Banco SQLite (`catalogo.db`) e Hash Lógico (`versao_catalogo`)

O banco local `generated/catalogo.db` possui três tabelas:

```sql
-- Tabela de croquis/picos
CREATE TABLE catalogo_croquis (
    croqui_uid TEXT PRIMARY KEY,   -- NanoID de 14 caracteres Base62
    id_slug TEXT NOT NULL,         -- ex: 'br_mg_ferros_pico_dos_ferros'
    nome TEXT NOT NULL,            -- ex: 'Pico dos Ferros'
    cidade TEXT,                   -- ex: 'Ferros'
    estado TEXT                    -- ex: 'MG'
);

-- Tabela de entidades endereçáveis por UID (escaladas, setores, grupos e botões)
CREATE TABLE catalogo_aresta (
    uid TEXT PRIMARY KEY,        -- NanoID de 14 caracteres Base62 da entidade
    tipo TEXT NOT NULL,          -- 'escalada', 'setor', 'grupo' ou 'botao'
    croqui_uid TEXT NOT NULL,    -- Chave lógica para catalogo_croquis
    nome TEXT NOT NULL,          -- Nome da escalada, setor, grupo ou texto do botão
    escalada_grau TEXT,          -- Grau da via (ex: '7a', 'V5', preenchido se tipo = 'escalada')
    escalada_tipo TEXT,          -- 'esportiva', 'tradicional', 'boulder', 'multienfiada', 'highline'
    setor_uid TEXT,              -- NanoID do setor (preenchido se tipo = 'escalada')
    grupo_uid TEXT               -- NanoID do grupo (preenchido em 'setor' e 'escalada' quando houver)
);

-- Tabela de metadados e versão lógica
CREATE TABLE catalogo_meta (
    chave TEXT PRIMARY KEY,        -- ex: 'versao_catalogo'
    valor TEXT NOT NULL            -- Hash SHA-256 curto (16 chars hex)
);

-- Índices otimizados
CREATE INDEX idx_catalogo_aresta_croqui ON catalogo_aresta(croqui_uid);
CREATE INDEX idx_catalogo_aresta_nome ON catalogo_aresta(nome COLLATE NOCASE);
CREATE INDEX idx_catalogo_aresta_tipo ON catalogo_aresta(tipo);
```

### Exemplo de Consulta para Metadados e Links Curtos (`aresta.cc/<uid>`)
Com a normalização por UID, o nome do setor e do grupo não são duplicados em cada linha de escalada. A resolução de todos os metadados textuais ocorre em $O(1)$ por chave primária via `LEFT JOIN`:

```sql
SELECT 
    e.nome AS escalada_nome,
    e.escalada_grau,
    e.escalada_tipo,
    s.nome AS setor_nome,
    g.nome AS grupo_nome,
    c.nome AS pico_nome,
    c.uf AS estado
FROM catalogo_aresta e
LEFT JOIN catalogo_aresta s ON s.uid = e.setor_uid
LEFT JOIN catalogo_aresta g ON g.uid = e.grupo_uid
LEFT JOIN catalogo_croquis c ON c.croqui_uid = e.croqui_uid
WHERE e.uid = ? AND e.tipo = 'escalada';

```

### Por que Hash Lógico Determinístico em vez de SHA-256 do arquivo `.db` ou Inteiro Sequencial?
- **Sem conflitos de Git**: Números sequenciais (`1, 2, 3...`) no repositório causariam conflitos constantes de merge entre branches.
- **Determinismo absoluto e preservação de bytes**: O schema não inclui timestamps voláteis e mantém paridade 1:1 com os croquis listados em `indice.binarypb` (expurgando registros órfãos). `calcular_versao_catalogo()` calcula um SHA-256 de 16 caracteres hexadecimais exclusivamente sobre as tuplas ordenadas de `catalogo_croquis` (`ORDER BY croqui_uid`) e `catalogo_aresta` (`ORDER BY uid`), levando menos de 15ms e garantindo que o mesmo conteúdo lógico produza sempre o mesmo hash e preserve os bytes de `catalogo.db` quando não há alterações catalogadas.

---

## 3. Pipeline de Geração (`deploy_generated.py`) e Serving (`update_serving.py`)

### 3.1. Compilação Local (`scripts/deploy_generated.py`)
1. **Passo A**: Compila os croquis para `compilado.binarypb`.
2. **Passo E**: Atualiza `generated/catalogo.db`, calcula `versao_catalogo` e persiste na tabela `catalogo_meta`.
3. **Passo C**: Grava `indice.binarypb` e `indice.yaml` incluindo `versao_catalogo`.
4. **Passo D**: Registra `catalogo.db` e seu checksum SHA-256 em `generated/arquivos_serving.yaml`.

### 3.2. Deploy Transacional D1 + R2 (`serving/update_serving.py`)
Executado no GitHub Actions (`.github/workflows/deploy.yml`) utilizando os secrets:
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_CATALOGO_D1_DATABASE_ID`
- `CLOUDFLARE_CATALOGO_D1_API_TOKEN`

Ordem estrita de execução:
1. Consulta o último `versao_hash` na tabela `deltas_catalogo` do D1. Se já for igual ao `versao_catalogo` do `generated/catalogo.db`, pula a etapa do D1.
2. Antes de enviar os novos arquivos ao R2, baixa o `catalogo.db` anterior publicado no R2 para um diretório temporário.
3. Se o banco D1 estiver vazio ou seu último `versao_hash` não corresponder ao `catalogo.db` anterior do R2, executa o **bootstrap completo** em lotes parametrizados. Caso contrário, calcula o diff via `scripts/gerar_deltas_catalogo.py` (`EXCEPT`), aplica os `upserts` e `deletes` no D1 e insere a nova linha em `deltas_catalogo`.
4. **Somente após o sucesso no D1**, envia os arquivos atualizados (`catalogo.db`, `indice.binarypb`, `arquivos_serving.yaml`, etc.) para o R2 e purga o cache da CDN.

---

## 4. Contrato do Cloudflare Worker (`catalogo.arestaclimb.com`)

Código-fonte localizado em `../aresta_backend/cloudflare/catalogo/`.

### 4.1. Endpoint `GET /sync`
- **URL**: `https://catalogo.arestaclimb.com/sync?versao_local=<hash_local>&versao_destino=<hash_destino>`
- **Comportamento**:
  1. Se `versao_local == versao_destino`: retorna imediatamente `acao: "apply_delta"` vazio com cache imutável.
  2. Busca os IDs numéricos (`id_local` e `id_destino`) na tabela `deltas_catalogo` correspondentes aos hashes informados.
  3. Se algum hash não existir no D1 ou `id_local > id_destino`: retorna fallback:
     ```json
     {
       "acao": "full_download",
       "versao_atual": "8f5027d0f987d808"
     }
     ```
     com cabeçalho `Cache-Control: no-store`.
  4. Caso `id_local < id_destino`: busca todos os registros com `id > id_local AND id <= id_destino ORDER BY id ASC`, realiza o **Delta Squash** em memória por chave primária (`croqui_uid` e `uid`) e retorna:
     ```json
     {
       "acao": "apply_delta",
       "versao_atual": "8f5027d0f987d808",
       "total_deltas": 2,
       "upserts": {
         "croquis": [...],
         "entidades": [...]
       },
       "deletes": {
         "croquis": [],
         "entidades": ["entidadeAntiga1234"]
       }
     }
     ```
     com cabeçalho `Cache-Control: public, max-age=31536000, s-maxage=31536000, immutable`.

### 4.2. Cache na Borda da CDN (Sem Consumo de Quota do Worker)
O Worker **não** utiliza `caches.default` internamente. O cache é feito inteiramente pela camada de CDN da Cloudflare antes do Worker ser invocado, através de uma **Cache Rule** configurada na zona `arestaclimb.com`:
- **Filtro**: `Hostname equals catalogo.arestaclimb.com` e `URI Path starts with /sync`
- **Cache Eligibility**: `Eligible for cache`
- **Edge TTL**: `Use cache-control header if present, bypass cache if not`

Assim, a primeira requisição para um par `(versao_local, versao_destino)` executa o Worker e armazena o resultado na CDN por 1 ano (`immutable`), e todas as requisições subsequentes de outros usuários para o mesmo par são respondidas diretamente pela CDN sem invocar o Worker nem o D1.

---

## 5. Mecanismo de Purge Global de Emergência (Kill Switch)

Para garantir recuperação instantânea caso uma inconsistência de dados ocorra nos clientes móveis, adotamos um mecanismo acionado via **Firebase Remote Config** (`catalogo_purge_timestamp`):

1. Cada build do aplicativo móvel (`aresta_app`) embute a constante `timestampBuildCatalogo`.
2. Na primeira instalação, `ultimo_purge_catalogo = max(timestampBuildCatalogo, firebase.catalogo_purge_timestamp)`, evitando downloads redundantes.
3. Se `catalogo_purge_timestamp` no Firebase for atualizado para um valor superior ao `ultimo_purge_catalogo` salvo no aparelho, o cliente descarta o `catalogo.db` local e baixa o `catalogo.db` completo diretamente de `https://serving.arestaclimb.com/<versao_serving>/catalogo.db`.
