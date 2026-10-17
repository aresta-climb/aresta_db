# Spec Delta

## Purpose

Estabelece o repositório `aresta_api` como fonte única de verdade (Single Source of Truth) para todos os contratos de comunicação do ecossistema Aresta — abrangendo esquemas relacionais SQL (`sql/*.sql`), especificações de APIs HTTP REST (`openapi/*.yaml`) e mensagens binárias Protobuf (`proto/*.proto`) — com geração determinística de código tipado para Python, Dart e TypeScript e validação formal de paridade.

## ADDED Requirements

### Requirement: Gerenciamento de dependências do aresta_api via uv
O repositório `aresta_api` SHALL gerenciar suas dependências e ferramentas de compilação/validação exclusivamente através do `uv`, possuindo arquivos `pyproject.toml` e `uv.lock` na raiz e dispensando o antigo `requirements.txt`.

#### Scenario: Execução de testes e build do aresta_api via uv
- **WHEN** `uv run pytest` ou `uv run python build.py` é executado no diretório `aresta_api`
- **THEN** o ambiente virtual utiliza as versões travadas em `uv.lock` (incluindo `grpcio-tools`, `mypy-protobuf`, `openapi-spec-validator`, `pyyaml`, `pytest`, `ruff` e `mypy`) sem exigir instalações manuais via `pip`.

### Requirement: Biblioteca geradora de contratos SQL multi-linguagem
O `aresta_api` SHALL fornecer a biblioteca modular `aresta_api/src/gerador_sql.py` (com seu respectivo teste `gerador_sql_test.py` e 100% de cobertura comportamental) que valida arquivos `.sql` em um banco SQLite em memória real (`:memory:`), extrai metadados das tabelas e colunas via `PRAGMA table_info` e gera arquivos `.py`, `.dart` e `.ts` contendo o DDL canônico e as definições tipadas das linhas de cada tabela.

#### Scenario: Validação e geração a partir de sql/catalogo.sql e sql/catalogo_d1.sql
- **WHEN** o gerador SQL processa `aresta_api/sql/catalogo.sql` e `aresta_api/sql/catalogo_d1.sql`
- **THEN** o gerador valida a execução sem erros no SQLite em memória e emite os módulos gerados em `aresta_api/sql/generated/` para Python (`TypedDict` e constantes DDL), Dart (classes com `fromMap`/`toMap` e constantes DDL) e TypeScript (`interface` e constantes DDL).

#### Scenario: Rejeição de arquivo SQL com erro de sintaxe
- **WHEN** um arquivo `.sql` com sintaxe inválida é submetido à biblioteca `gerador_sql.py`
- **THEN** a execução no SQLite `:memory:` falha imediatamente levantando exceção descritiva antes de emitir qualquer arquivo gerado.

### Requirement: Biblioteca geradora de contratos OpenAPI 3.1 multi-linguagem
O `aresta_api` SHALL fornecer a biblioteca modular `aresta_api/src/gerador_openapi.py` (com seu respectivo teste `gerador_openapi_test.py` e 100% de cobertura comportamental) que valida arquivos `.yaml` em `aresta_api/openapi/` utilizando `openapi-spec-validator` e emite módulos gerados em Python, Dart e TypeScript contendo constantes de URLs dos servidores (`servers`), constantes de rotas (`paths`) e tipos estruturais para parâmetros e payloads (`components/schemas`).

#### Scenario: Validação formal e geração para todas as APIs do backend
- **WHEN** o gerador OpenAPI processa `catalogo.yaml`, `previa.yaml`, `colaboracao.yaml` e `feedback.yaml`
- **THEN** cada arquivo é validado contra a especificação OpenAPI 3.1 e os respectivos artefatos `.py`, `.dart` e `.ts` são gerados em `aresta_api/openapi/generated/` com constantes de URL base, rotas e estruturas de dados tipadas.

#### Scenario: Rejeição de especificação OpenAPI inválida
- **WHEN** um arquivo `.yaml` viola o schema oficial da especificação OpenAPI 3.1
- **THEN** `openapi-spec-validator` rejeita a especificação e interrompe o build com erro explícito.

### Requirement: Validação de paridade 1:1 entre tabelas SQL e schemas OpenAPI
O `aresta_api` SHALL fornecer a biblioteca modular `aresta_api/src/validador_paridade.py` (com seu respectivo teste `validador_paridade_test.py` e 100% de cobertura comportamental) para verificar que as tabelas relacionais em `sql/*.sql` possuem exatamente as mesmas colunas, tipos equivalentes e obrigatoriedade que seus schemas correspondentes em `openapi/*.yaml`.

#### Scenario: Paridade verificada entre catalogo.sql e catalogo.yaml
- **WHEN** o validador de paridade compara as tabelas `catalogo_croquis` e `catalogo_aresta` de `sql/catalogo.sql` com os schemas `CatalogoCroqui` e `CatalogoEntidade` de `openapi/catalogo.yaml`
- **THEN** a validação confirma que os nomes das colunas, tipos de dados e nulabilidade coincidem perfeitamente.

#### Scenario: Detecção de divergência entre coluna SQL e propriedade OpenAPI
- **WHEN** uma coluna é adicionada, removida ou tem seu tipo/nulabilidade alterado no `.sql` sem a atualização correspondente no schema do `.yaml` (ou vice-versa)
- **THEN** o validador de paridade levanta erro apontando a coluna/propriedade divergente.

### Requirement: Compilação unificada no build.py e consumo em aresta_db e aresta_backend
O script `aresta_api/build.py` SHALL orquestrar a compilação de `proto/`, `sql/` e `openapi/`, e tanto `aresta_db` quanto `aresta_backend` SHALL consumir os artefatos gerados a partir do `aresta_api` sem quebrar nenhum teste comportamental existente.

#### Scenario: Execução de build.py gera todos os artefatos atualizados
- **WHEN** `build.py` é executado no `aresta_api`
- **THEN** os diretórios `proto/generated/`, `sql/generated/` e `openapi/generated/` são atualizados deterministicamente e verificados por hash.

#### Scenario: Preservação integral do comportamento nas suítes de aresta_db e aresta_backend
- **WHEN** `aresta_db` e `aresta_backend` passam a importar os tipos, rotas e DDL gerados pelo `aresta_api`
- **THEN** todos os testes existentes de `aresta_db` (`pytest` + `mypy --strict`) e de `aresta_backend` (`deno test`) continuam passando integralmente sem regressão.
