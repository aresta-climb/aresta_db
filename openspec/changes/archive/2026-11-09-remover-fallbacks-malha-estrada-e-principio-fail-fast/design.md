# Design

## Context

O job `deploy` em `.github/workflows/deploy.yml` executa `python3 -u serving/update_serving.py` diretamente no Python do sistema do `ubuntu-latest` (que possui `boto3` e a biblioteca padrão, mas não instala `protobuf`). O `update_serving.py` importa `serving/sincronizar_d1_lib.py` e `scripts/gerar_deltas_catalogo.py`, que importam `obter_versao_catalogo` de `scripts/gerar_catalogo_sqlite_lib.py`. Quando `scripts/gerar_catalogo_sqlite_lib.py` manteve o fallback legado de `cliente_overpass` e importou `scripts/gerar_malha_estrada_lib.py` no topo do arquivo, o import transitivo de `aresta_api.proto.generated.croqui_pb2` passou a quebrar o deploy com `ModuleNotFoundError: No module named 'google'` (Issues #89 e #90).

## Goals / Non-Goals

**Goals:**
- Estabelecer o Princípio VIII (`Fail-Fast e Proibição de Fallbacks Legados ou Silenciosos`, com *escape hatch* explícita mediante pedido do usuário) e padronizar o Princípio IX (`Responsividade Inegociável da UI`) nos `AGENTS.md` do ecossistema Aresta.
- Remover o fallback legado `cliente_overpass` de `gerar_catalogo_completo()` e eliminar qualquer import de `scripts/gerar_malha_estrada_lib.py` em `scripts/gerar_catalogo_sqlite_lib.py` e no `.github/workflows/deploy.yml`.
- Eliminar o `try/except ImportError: croqui_pb2 = None` no topo de `scripts/gerar_catalogo_sqlite_lib.py` e o `try/except Exception: pass` em `_migracao_afeta_serving` (`serving/update_serving.py`).

**Non-Goals:**
- Alterar as rotinas de migração de schema SQLite/D1 em `inicializar_banco_catalogo()` e `inicializar_schema_d1()`, pois elas são responsáveis por atualizar o schema do banco Cloudflare D1 e do `catalogo_anterior.db` baixado do R2 durante o deploy.

## Decisions

### 1. Desacoplamento de `gerar_catalogo_sqlite_lib.py` sem `try/except ImportError`
- **Decisão**:
  - Remover o parâmetro `cliente_overpass` de `gerar_catalogo_completo()` e o import de `scripts.gerar_malha_estrada_lib`.
  - Manter a validação de sincronia da malha (`_malha_estrada_pico_atualizada`) e extração de linhas (`_extrair_linhas_malha_de_pico_proto`) diretamente em `scripts/gerar_catalogo_sqlite_lib.py` operando sobre os atributos do `Pico` já carregado.
  - Importar `from aresta_api.proto.generated import croqui_pb2` sob `if TYPE_CHECKING:` para anotações estáticas e explicitamente (sem `try/except`) dentro de `formatar_grau_escalada()` e `gerar_catalogo_completo()`.
- **Racional**: Assim, quem importa `gerar_catalogo_sqlite_lib` apenas para operações de banco SQLite (`obter_versao_catalogo`, `inicializar_banco_catalogo`, `calcular_versao_catalogo`) no `deploy.yml` não carrega `google.protobuf` nem `gerar_malha_estrada_lib`, e quem chama funções de compilação de Protobuf sem `protobuf` instalado recebe `ModuleNotFoundError` imediato (Fail-Fast).

### 2. Fail-Fast em `_migracao_afeta_serving` (`serving/update_serving.py`)
- **Decisão**: Remover `if not hasattr(arquivo, "read_text")` e o bloco `try ... except Exception: pass` em `_migracao_afeta_serving(arquivo: Path)`.
- **Racional**: Se um arquivo `.py` dentro de `migracoes/` estiver corrompido ou com erro de sintaxe, `ast.parse` deve levantar `SyntaxError` imediatamente em vez de mascarar o erro assumindo `True`.

## Risks / Trade-offs

- **[Risco] Regressão futura reintroduzindo imports de Protobuf no caminho de `update_serving.py`** → **Mitigação**: Adicionar teste comportamental em `serving/update_serving_test.py` verificando que a importação e execução de `update_serving` e `sincronizar_d1_lib` funcionam mesmo bloqueando `google.protobuf` e `scripts.gerar_malha_estrada_lib` em `sys.modules`.
