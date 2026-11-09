# Tasks

## 1. Unificação dos Princípios VIII, IX e X nos `AGENTS.md` do Ecossistema Aresta

- [x] 1.1 Atualizar `c:\Renato\Devel\aresta-climb\aresta_db\AGENTS.md` e `c:\Renato\Devel\aresta-climb\aresta_db\openspec\config.yaml` adicionando o Princípio VIII (`Fail-Fast e Proibição de Fallbacks Legados ou Silenciosos` com *escape hatch* explícita), posicionando `Responsividade Inegociável da UI` como IX e `Edições de Estado via Comandos do Histórico (Undo/Redo)` como X
- [x] 1.2 Atualizar `c:\Renato\Devel\aresta-climb\aresta_db\aresta_api\AGENTS.md`, `c:\Renato\Devel\aresta-climb\aresta_app\AGENTS.md`, `c:\Renato\Devel\aresta-climb\aresta_backend\AGENTS.md` e `c:\Renato\Devel\aresta-climb\arestaclimb.com\AGENTS.md` com o Princípio VIII compartilhado, Princípio IX de Responsividade nos repositórios com UI e renumeração dos princípios específicos

## 2. Remoção de Fallbacks Legados no Catálogo SQLite e no Deploy (`aresta_db`)

- [x] 2.1 Atualizar os testes em `scripts/gerar_catalogo_sqlite_lib_test.py` e `serving/update_serving_test.py` (fase Red do TDD): remover o teste do fallback legado `cliente_overpass`, exigir que `_migracao_afeta_serving` propague `SyntaxError` em arquivos inválidos (Fail-Fast) e adicionar teste garantindo que `update_serving` funciona com `google.protobuf` e `scripts.gerar_malha_estrada_lib` bloqueados em `sys.modules`
- [x] 2.2 Remover `cliente_overpass`, o import de `scripts.gerar_malha_estrada_lib` e o `try/except ImportError: croqui_pb2 = None` de `scripts/gerar_catalogo_sqlite_lib.py`; remover o `try/except Exception: pass` de `_migracao_afeta_serving` em `serving/update_serving.py`; e remover `scripts/gerar_malha_estrada_lib.py` de `.github/workflows/deploy.yml`, validando 100% de cobertura nos testes e tipagem estática
