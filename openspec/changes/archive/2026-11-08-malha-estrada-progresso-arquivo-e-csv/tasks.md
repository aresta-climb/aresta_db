# Tasks

## 1. Contrato Protobuf (`ArquivoMalhaEstrada`) no `aresta_api`

- [x] 1.1 Escrever testes em `aresta_api/tests/test_contratos_sql_openapi.py` validando a mensagem `ArquivoMalhaEstrada` (`oneof arquivo { caminho, conteudo }`) e o campo `Pico.malha_estrada` em `croqui.proto`, atualizar `aresta_api/proto/croqui.proto`, regenerar os artefatos com `uv run python scripts/compilar_contratos.py` e verificar que `uv run pytest` em `aresta_api` passa com 100% de sucesso.

## 2. Otimização da Query Overpass, Progresso e Cancelamento em `gerar_malha_estrada_lib.py`

- [x] 2.1 Adicionar testes em `tests/scripts/test_gerar_malha_estrada_lib.py` cobrindo o micro-anel de 4 km (`around:4000`) para vias locais (`residential|living_street|service|track`), o Anel 1 (`around:15000`) até `unclassified`, o callback de progresso (`ao_progresso`), o cancelamento cooperativo (`verificador_cancelamento` / `ErroMalhaEstradaCancelada`) e a leitura/escrita em `pico.malha_estrada.conteudo`, implementar as mudanças em `scripts/gerar_malha_estrada_lib.py` e verificar 100% de cobertura com `uv run pytest tests/scripts/test_gerar_malha_estrada_lib.py`.

## 3. Persistência Separada em `malha_estrada.yaml` no `CroquiModel` e Pipeline de Compilação

- [x] 3.1 Adicionar testes em `tests/editor/models/test_croqui_model.py` e `tests/scripts/test_preparar_submissao_lib.py` verificando que `CroquiModel.extrair_arquivos_e_serializar` grava `malha_estrada.yaml` separado e deixa `malha_estrada: { caminho: malha_estrada.yaml }` no `croqui.yaml`, `CroquiModel.carregar_do_disco` hidrata `pico.malha_estrada.conteudo`, `limpar_arquivos_nao_utilizados` / `corrigir_database` preservam e validam SPDX em `malha_estrada.yaml`, e `compilar_croqui` expande `malha_estrada.conteudo` no `compilado.binarypb`; implementar em `editor/models/croqui_model.py` e `scripts/preparar_submissao_lib.py` e verificar os testes passando.

## 4. Exportação de `catalogo_nos_estrada.csv` e `catalogo_distancias_estrada.csv` no Catálogo SQLite

- [x] 4.1 Atualizar testes em `tests/scripts/test_gerar_catalogo_sqlite_lib.py` e `tests/scripts/test_deploy_generated.py` para validar a leitura de `pico.malha_estrada.conteudo` e a exportação determinística dos 5 arquivos CSV (`catalogo_croquis.csv`, `catalogo_aresta.csv`, `catalogo_nos_estrada.csv`, `catalogo_distancias_estrada.csv` e `catalogo_meta.csv`) com short-circuit de inalterados, implementar em `scripts/gerar_catalogo_sqlite_lib.py` e `scripts/deploy_generated.py` e verificar 100% de cobertura nos módulos alterados.

## 5. Janela Modal de Progresso em Background (`QThread`) no Editor

- [x] 5.1 Escrever testes de widget em `tests/editor/views/inspector/test_widget_mensagem_coordenada.py` cobrindo a abertura de `DialogoProgressoMalhaEstrada`, atualização de barra/log de etapas via `WorkerGeracaoMalhaEstrada`, conclusão gravando `pico.malha_estrada.conteudo` no controlador e cancelamento pelo botão `Cancelar` sem modificar o modelo; implementar em `editor/views/inspector/widget_mensagem_coordenada.py` e verificar 100% de cobertura e `mypy --strict` limpo.
