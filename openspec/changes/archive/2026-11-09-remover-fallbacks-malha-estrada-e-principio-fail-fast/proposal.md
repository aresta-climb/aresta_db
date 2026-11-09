# Proposal

## Why

O workflow de deploy para Cloudflare R2 e D1 (`.github/workflows/deploy.yml`, Issues #89 e #90) está falhando ao executar `python3 -u serving/update_serving.py` porque `scripts/gerar_catalogo_sqlite_lib.py` mantinha um fallback legado opcional `cliente_overpass` e importava `scripts/gerar_malha_estrada_lib.py` no topo do módulo — o qual, por sua vez, importava `aresta_api.proto.generated.croqui_pb2` (`google.protobuf`), indisponível no Python nativo do runner de deploy. Além disso, a manutenção de fallbacks legados e blocos `try/except` silenciosos mascara erros e cria acoplamentos fantasmas. Precisamos institucionalizar o princípio de **Fail-Fast e Proibição de Fallbacks Legados ou Silenciosos** em todos os `AGENTS.md` do ecossistema Aresta e remover os fallbacks legados e silenciosos de `gerar_catalogo_sqlite_lib.py` e `update_serving.py`.

## What Changes

- **Unificação dos Princípios nos `AGENTS.md` do Ecossistema Aresta**:
  - Adicionar o **Princípio VIII: Fail-Fast e Proibição de Fallbacks Legados ou Silenciosos** (com *escape hatch* explícita exclusivamente quando solicitado pelo usuário) em `aresta_db`, `aresta_api`, `aresta_app`, `aresta_backend` e `arestaclimb.com`.
  - Unificar o **Princípio IX: Responsividade Inegociável da UI e Execução Pesada em Background (Orçamento de Meio Frame)** nos repositórios com interface (`aresta_db`, `aresta_app` e `arestaclimb.com`), posicionando os princípios específicos de cada repositório em **X** (ou **IX** nos repositórios sem UI).
- **Remoção do Fallback Legado `cliente_overpass` e Desacoplamento de `gerar_malha_estrada_lib.py` em `scripts/gerar_catalogo_sqlite_lib.py`**:
  - Remover o parâmetro `cliente_overpass` e a chamada a `gerar_malha_estrada_pico` de `gerar_catalogo_completo()`, tornando a compilação do catálogo estritamente 100% offline a partir de `pico.malha_estrada.conteudo`.
  - Eliminar o import de `scripts.gerar_malha_estrada_lib` e o `try/except ImportError: croqui_pb2 = None` de `scripts/gerar_catalogo_sqlite_lib.py`, importando `croqui_pb2` apenas nas funções de compilação de Protobuf (`gerar_catalogo_completo` e `formatar_grau_escalada`) para que o deploy (`obter_versao_catalogo`) opere apenas com a biblioteca padrão (`sqlite3`) e quem compilar sem `protobuf` falhe imediatamente (Fail-Fast).
  - Remover `scripts/gerar_malha_estrada_lib.py` de `paths` e `sparse-checkout` em `.github/workflows/deploy.yml`.
- **Fail-Fast em `_migracao_afeta_serving` (`serving/update_serving.py`)**:
  - Remover o bloco `try/except Exception: pass` e o fallback defensivo `hasattr(arquivo, "read_text")` em `_migracao_afeta_serving()`, garantindo que erros de leitura ou de sintaxe em scripts de migração falhem ruidosamente.

## Capabilities

### New Capabilities

### Modified Capabilities
- `catalogo-sqlite-delta-sync`: Remove qualquer acoplamento do gerador de catálogo SQLite e do script de deploy (`update_serving.py`) com `gerar_malha_estrada_lib.py` e garante execução do deploy sem dependência de `google.protobuf`.

## Impact

- **`AGENTS.md` nos 5 repositórios**: `aresta_db/AGENTS.md` (e `openspec/config.yaml`), `aresta_api/AGENTS.md`, `aresta_app/AGENTS.md`, `aresta_backend/AGENTS.md`, `arestaclimb.com/AGENTS.md`.
- **`aresta_db`**: `.github/workflows/deploy.yml`, `scripts/gerar_catalogo_sqlite_lib.py`, `scripts/gerar_catalogo_sqlite_lib_test.py`, `serving/update_serving.py`, `serving/update_serving_test.py`.
