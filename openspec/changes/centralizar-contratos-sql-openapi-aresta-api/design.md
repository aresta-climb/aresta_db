# Design

## Context

O ecossistema Aresta comunica dados entre três repositórios principais (`aresta_db` em Python, `aresta_backend` em Deno/TypeScript e `aresta_app` em Flutter/Dart) utilizando três canais distintos:
1. Arquivos binários Protobuf servidos via HTTPS (`compilado.binarypb`, `indice.binarypb`, `betas_pendentes.binarypb`).
2. Banco relacional SQLite (`catalogo.db` servido via HTTPS e espelhado no Cloudflare D1).
3. Endpoints HTTP REST nos Cloudflare Workers (`catalogo`, `previa`, `feedback`) e nas Supabase Edge Functions (`create-pr`, `git-proxy`, `app-feedback`, `discord-feedback`).

Enquanto o canal 1 já é governado por `aresta_api/proto/*.proto`, os canais 2 e 3 estavam definidos de forma ad-hoc em cada repositório. Consultar `proposal.md` para a motivação completa.

## Goals / Non-Goals

**Goals:**
- Migrar `aresta_api` de `pip`/`requirements.txt` para `uv` (`pyproject.toml` + `uv.lock`).
- Criar bibliotecas modulares e 100% testadas em `aresta_api/src/` (`gerador_sql.py`, `gerador_openapi.py`, `validador_paridade.py`).
- Especificar formalmente `sql/catalogo.sql`, `sql/catalogo_d1.sql` e `openapi/{catalogo,previa,colaboracao,feedback}.yaml` (incluindo URLs de `servers`, `paths` e `components/schemas`).
- Emitir código determinístico em Python (`.py`), Dart (`.dart`) e TypeScript (`.ts`) a partir de `aresta_api/build.py`.
- Integrar os contratos gerados em `aresta_db` e `aresta_backend` preservando 100% dos testes comportamentais existentes.

**Non-Goals:**
- Alterar o formato dos payloads JSON ou das tabelas SQLite já em uso em produção.
- Adicionar bibliotecas pesadas de runtime nos Cloudflare Workers ou nas Supabase Edge Functions.

## Decisions

### 1. Tríade de Contratos (`proto/` + `sql/` + `openapi/`) em vez de Protobuf para Tudo
- **Decisão**: Utilizar `.proto` para arquivos binários, `.sql` puro para esquemas SQLite/D1 e `OpenAPI 3.1 (.yaml)` para rotas e payloads HTTP REST.
- **Racional**:
  - Tentar modelar SQLite via `field options` no Protobuf exigiria construir um mini-ORM customizado para lidar com `PRIMARY KEY`, `AUTOINCREMENT`, `COLLATE NOCASE` e índices.
  - Usar Proto3 JSON para APIs REST introduz atritos severos de conversão `snake_case` vs `camelCase` no Dart e omissão padrão de campos vazios/zeros (`0`, `[]`), além de não especificar URLs de servidores, query parameters, path parameters nem status HTTP (`200`, `201`, `307`, `400`, `401`, `409`).
- **Alternativas consideradas**:
  - *Protobuf com `field options` para SQL e REST*: Rejeitado por violar o Princípio VI (Simplicidade e Anti-Abstração).

### 2. Validação Oficial (`openapi-spec-validator` + `sqlite3`) + Emissor Enxuto em `aresta_api/src/`
- **Decisão**: Validar os arquivos `openapi/*.yaml` com a biblioteca oficial `openapi-spec-validator` e os arquivos `sql/*.sql` executando-os no motor `sqlite3` (`:memory:`) da stdlib do Python, emitindo os arquivos `.py`, `.dart` e `.ts` através de bibliotecas próprias em `aresta_api/src/`.
- **Racional**:
  - Não reinventamos a validação do padrão OpenAPI 3.1 nem do parser SQL.
  - Evitamos depender de `openapi-generator` (que exige Java/JVM e gera dezenas de arquivos boilerplate incompatíveis com nossos linters `mypy --strict` e `ruff`).
  - Nosso emissor extrai diretamente o bloco `servers` (URLs canônicas dos serviços) e `paths` (rotas HTTP) como constantes tipadas de primeira classe nas três linguagens.

### 3. Separação entre `sql/catalogo.sql` e `sql/catalogo_d1.sql`
- **Decisão**: Manter as três tabelas do catálogo (`catalogo_croquis`, `catalogo_aresta`, `catalogo_meta`) em `sql/catalogo.sql` e a tabela de histórico de deltas da borda (`deltas_catalogo`) em `sql/catalogo_d1.sql`.
- **Racional**: O arquivo `generated/catalogo.db` baixado pelo aplicativo móvel não deve conter a tabela `deltas_catalogo` vazia, enquanto o Cloudflare D1 precisa de ambos os esquemas formalmente especificados e tipados.

### 4. Tipagem Estrutural Zero-Cost (`TypedDict` em Python e `interface` em TypeScript)
- **Decisão**: Emitir `TypedDict` nos módulos Python gerados e `interface` / `type` nos módulos TypeScript gerados (e classes DTO com `fromMap`/`toMap` e `fromJson`/`toJson` em Dart).
- **Racional**: Em tempo de execução, `TypedDict` é um `dict` nativo do Python e `interface` tem custo zero no bundle JS do Cloudflare Worker / Deno. Isso permite tipar estritamente `aresta_db` (`mypy --strict`) e `aresta_backend` (`deno test`) mantendo 100% de compatibilidade com os testes unitários e de integração existentes.

## Risks / Trade-offs

- **[Risco] Divergência manual entre colunas de `sql/catalogo.sql` e propriedades de `openapi/catalogo.yaml`** → **Mitigação**: A biblioteca `aresta_api/src/validador_paridade.py` inspeciona as colunas reais via `PRAGMA table_info` no SQLite em memória e falha o teste e o `build.py` caso haja qualquer diferença de nome, tipo ou nulabilidade em relação aos schemas `CatalogoCroqui` e `CatalogoEntidade` no OpenAPI.
- **[Risco] Artefatos gerados desatualizados após edição de `.sql` ou `.yaml`** → **Mitigação**: `build.py` calcula o hash SHA-256 combinado de todos os arquivos `.proto`, `.sql` e `.yaml` e os testes de validação verificam se os arquivos em `generated/` estão sincronizados.

## Migration Plan

1. Configurar `pyproject.toml` e `uv.lock` em `aresta_api` e remover `requirements.txt`.
2. Desenvolver sob TDD (`Red-Green-Refactor`) as bibliotecas em `aresta_api/src/` (`gerador_sql.py`, `gerador_openapi.py`, `validador_paridade.py`) com 100% de cobertura.
3. Escrever `sql/catalogo.sql`, `sql/catalogo_d1.sql` e `openapi/{catalogo,previa,colaboracao,feedback}.yaml`.
4. Atualizar `aresta_api/build.py` e gerar `sql/generated/` e `openapi/generated/`.
5. Integrar os contratos gerados em `aresta_db` e `aresta_backend`, validando que todas as suítes de testes e linters passam sem regressões.
