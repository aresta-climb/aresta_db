# Tasks

## 1. Contrato Protobuf no `aresta_api` (`Pico.malha_estrada`)

- [x] 1.1 Escrever testes em `aresta_api/tests/test_croqui.py` (fase Red do TDD) validando a presença e serialização de `NoMalhaEstrada` e `MalhaEstradaPico` (`latitude_referencia_e7`, `longitude_referencia_e7` e `repeated NoMalhaEstrada nos`) no campo `Pico.malha_estrada`, verificando a falha inicial com `uv run pytest aresta_api/tests/test_croqui.py`
- [x] 1.2 Adicionar `NoMalhaEstrada`, `MalhaEstradaPico` e `Pico.malha_estrada = 15` em `aresta_api/proto/croqui.proto`, recompilar os artefatos com `uv run python build.py -f` em `aresta_api` e verificar que `uv run pytest aresta_api/tests/` passa integralmente

## 2. Failover de Espelhos Oficiais e Populamento de `MalhaEstradaPico` (`scripts/gerar_malha_estrada_lib.py`)

- [x] 2.1 Escrever testes comportamentais em `scripts/gerar_malha_estrada_lib_test.py` (fase Red do TDD) cobrindo o failover automático entre múltiplos espelhos públicos no `ClienteOverpass` e os helpers `malha_estrada_pico_atualizada()` e `popular_malha_estrada_em_pico_proto()`, verificando a falha inicial com `uv run pytest scripts/gerar_malha_estrada_lib_test.py`
- [x] 2.2 Implementar o failover de espelhos públicos da Overpass API em `ClienteOverpass` e os helpers de validação/conversão de `MalhaEstradaPico` em `scripts/gerar_malha_estrada_lib.py`, verificando 100% de cobertura com `uv run pytest scripts/gerar_malha_estrada_lib_test.py --cov=scripts.gerar_malha_estrada_lib --cov-report=term-missing`

## 3. Botão `Gerar Mapa de Pontos` e Warning Exclusivos para `Pico.localizacao` no Editor Desktop

- [x] 3.1 Escrever testes comportamentais em `editor/views/widget_mensagem_coordenada_test.py` e `editor/views/widget_editor_dados_test.py` (fase Red do TDD) verificando: (a) exibição do warning e do botão `Gerar Mapa de Pontos` exclusivamente quando vinculado a `Pico.localizacao`; (b) omissão do botão e do warning em coordenadas de `Setor`, `Grupo` e `PontoDeInteresse`; (c) geração da malha com suporte a Undo/Redo ao clicar no botão ou editar/colar coordenadas do Pico usando `ClienteOverpassFake`; e (d) degradação graciosa sem bloquear a edição quando a rede falhar, validando a falha inicial com `uv run pytest editor/views/widget_mensagem_coordenada_test.py`
- [x] 3.2 Implementar o suporte a `msg_pico` e `cliente_overpass` em `editor/views/widget_mensagem_coordenada.py` e a passagem de `msg_pico` para `Pico.localizacao` em `editor/views/widget_editor_dados.py`, verificando 100% de cobertura com `uv run pytest editor/views/widget_mensagem_coordenada_test.py --cov=editor.views.widget_mensagem_coordenada --cov-report=term-missing`

## 4. Compilação 100% Offline e Warning de Compilação (`deploy_generated.py` e `gerar_catalogo_sqlite_lib.py`)

- [x] 4.1 Escrever testes comportamentais em `scripts/gerar_catalogo_sqlite_lib_test.py` e `scripts/deploy_generated_test.py` (fase Red do TDD) validando: (a) extração 100% offline de `pico.malha_estrada` do `compilado.binarypb` para `catalogo_nos_estrada` e `catalogo_distancias_estrada` quando sincronizada com `pico.localizacao`; (b) descarte de malha defasada quando a coordenada do pico divergir de `latitude_referencia_e7`/`longitude_referencia_e7`; e (c) emissão de `Aviso:` em `deploy_generated.py` quando um Pico com localização válida não possuir malha atualizada, verificando a falha inicial com `uv run pytest scripts/gerar_catalogo_sqlite_lib_test.py scripts/deploy_generated_test.py`
- [x] 4.2 Implementar a leitura offline de `pico.malha_estrada` em `scripts/gerar_catalogo_sqlite_lib.py`, a verificação de aviso `verificar_malha_estrada_pico` em `scripts/deploy_generated.py`, atualizar `.github/workflows/deploy.yml` (`sparse-checkout`) e `docs/catalogo_sqlite_e_delta_sync.md`, verificando 100% de cobertura em `scripts/gerar_catalogo_sqlite_lib.py` e aprovação em `tests/tipagem_estatica_test.py`
