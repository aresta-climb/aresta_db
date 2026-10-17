# Proposal

## Why

Atualmente, enquanto os dados binários de croquis e índices possuem contratos estritos definidos em Protobuf no `aresta_api`, o esquema relacional do catálogo SQLite (`catalogo.db` e Cloudflare D1) e os contratos das APIs HTTP REST do `aresta_backend` (Cloudflare Workers de Catálogo, Prévia e Feedback, além das Supabase Edge Functions de Colaboração e Feedback) estão espalhados manualmente entre strings SQL no Python, interfaces avulsas em TypeScript e dicionários sem contrato compartilhado. Essa fragmentação gera risco constante de dessincronização silenciosa (*drift*) entre os produtores e consumidores de dados em Python (`aresta_db`), TypeScript (`aresta_backend`) e Dart (`aresta_app`).

## What Changes

- **Migração do `aresta_api` para `uv`**: Substituição do antigo `requirements.txt` por `pyproject.toml` e `uv.lock` no repositório `aresta_api`, incluindo `openapi-spec-validator`, `pyyaml`, `grpcio-tools`, `mypy-protobuf`, `pytest`, `ruff` e `mypy`, além da atualização do workflow `.github/workflows/generate_protobuf.yml` para utilizar `uv`.
- **Bibliotecas Geradoras e de Paridade em `aresta_api/src/`**:
  - `aresta_api/src/gerador_sql.py` (e `gerador_sql_test.py`): Valida arquivos `.sql` executando-os em um banco SQLite `:memory:` real, extrai metadados via `PRAGMA table_info` e emite módulos gerados em Python (`.py`), Dart (`.dart`) e TypeScript (`.ts`) contendo as constantes DDL canônicas, nomes de tabelas/colunas e tipos estruturais (`TypedDict`, classes Dart e `interface` TS).
  - `aresta_api/src/gerador_openapi.py` (e `gerador_openapi_test.py`): Valida especificações OpenAPI 3.1 com `openapi-spec-validator`, extrai URLs base (`servers`), rotas e parâmetros (`paths`) e modelos de dados (`components/schemas`), gerando código estritamente tipado e sem sobrecarga de runtime em Python, Dart e TypeScript.
  - `aresta_api/src/validador_paridade.py` (e `validador_paridade_test.py`): Garante matematicamente a paridade 1:1 de colunas e tipos entre tabelas definidas em `sql/*.sql` e seus schemas correspondentes em `openapi/*.yaml`.
- **Contratos Relacionais em `aresta_api/sql/`**:
  - `sql/catalogo.sql`: Esquema canônico das tabelas `catalogo_croquis`, `catalogo_aresta` e `catalogo_meta` (e seus índices), compartilhado entre o SQLite local e o Cloudflare D1.
  - `sql/catalogo_d1.sql`: Esquema canônico complementar exclusivo da borda Cloudflare D1 contendo a tabela `deltas_catalogo` e seu índice.
- **Contratos de APIs REST em `aresta_api/openapi/`**:
  - `openapi/catalogo.yaml`: Contrato completo do Cloudflare Worker de Catálogo (`https://catalogo.arestaclimb.com`: `/health` e `/sync`).
  - `openapi/previa.yaml`: Contrato completo do Cloudflare Worker de Prévia Ao Vivo (`https://previa.arestaclimb.com`: `/health`, `/sessoes`, `/sessions`, `/{codigo}/meta`).
  - `openapi/colaboracao.yaml`: Contrato das Supabase Edge Functions de publicação (`/create-pr` e `/git-proxy`).
  - `openapi/feedback.yaml`: Contrato do Cloudflare Worker Gateway de Feedback (`https://feedback.arestaclimb.com`: `/health`, `/diagnostico/{id}`, `/anexos/{caminho}`) e das Edge Functions (`/app-feedback` e `/discord-feedback`).
- **Orquestração Unificada em `aresta_api/build.py`**: Atualização do `build.py` para compilar de forma determinística `proto/`, `sql/` e `openapi/`, regerando os artefatos nas três linguagens.
- **Integração em `aresta_db` e `aresta_backend` com Zero Regressão**:
  - Inclusão do `aresta_api` no `aresta_backend` e adoção das constantes DDL, rotas e tipos gerados tanto em `aresta_db` quanto em `aresta_backend`, mantendo as suítes de testes comportamentais existentes passando sem quebra de contrato.

## Capabilities

### New Capabilities
- `contratos-sql-e-openapi-aresta-api`: Arquitetura de contratos relacionais (`.sql`) e de APIs REST (`openapi/*.yaml`) no `aresta_api`, com validação formal, verificação de paridade 1:1, gerenciamento via `uv` e geração automatizada de código para Python, Dart e TypeScript.

### Modified Capabilities
- `catalogo-sqlite-delta-sync`: O schema relacional do catálogo SQLite (`catalogo.sql` e `catalogo_d1.sql`) e os contratos do endpoint `/sync` (`openapi/catalogo.yaml`) passam a ser importados diretamente dos artefatos gerados pelo `aresta_api`.

## Impact

- **`aresta_api`**: Adição de `pyproject.toml`, `uv.lock`, `src/`, `sql/`, `openapi/`, atualização de `build.py` e `.github/workflows/generate_protobuf.yml`, remoção de `requirements.txt`.
- **`aresta_db`**: Refatoração de `scripts/gerar_catalogo_sqlite_lib.py`, `scripts/gerar_deltas_catalogo.py`, `serving/sincronizar_d1_lib.py` e clientes HTTP do editor para consumirem as constantes SQL, URLs e `TypedDict` gerados por `aresta_api`.
- **`aresta_backend`**: Consumo das interfaces TypeScript, constantes de rotas e DDL SQL gerados por `aresta_api` nos Workers (`catalogo`, `previa`, `feedback`) e Supabase Edge Functions (`create-pr`, `git-proxy`, `app-feedback`, `discord-feedback`).
