# Tasks

## 1. Campo `versao = 4` em `MalhaEstradaPico` (`aresta_api`)

- [x] 1.1 Adicionar `int32 versao = 4;` em `MalhaEstradaPico` (`aresta_api/proto/croqui.proto`), executar `build.py` e validar que o campo `versao` está disponível em `croqui_pb2.MalhaEstradaPico`

## 2. `VERSAO_ATUAL_MALHA_ESTRADA = 2` e Validação de Versão (`gerar_malha_estrada_lib.py`)

- [x] 2.1 Escrever testes em `scripts/gerar_malha_estrada_lib_test.py` e `scripts/deploy_generated_test.py` validando: (a) `VERSAO_ATUAL_MALHA_ESTRADA == 2` gravada por `construir_malha_estrada_pico_proto`; (b) `malha_estrada_pico_sincronizada(pico)` retorna `True` mesmo com `versao < 2` (permitindo que `extrair_linhas_malha_de_pico_proto` continue extraindo linhas para o catálogo); e (c) `malha_estrada_pico_atualizada(pico)` retorna `False` quando `versao < 2` e `True` quando `versao >= 2` (Red)
- [x] 2.2 Implementar `VERSAO_ATUAL_MALHA_ESTRADA = 2`, `obter_versao_malha_estrada_pico`, `malha_estrada_pico_sincronizada` e `malha_estrada_pico_atualizada` em `scripts/gerar_malha_estrada_lib.py`, verificando 100% de cobertura com `pytest` (Green)

## 3. Pontuação Parcial (`700/1000` pts) no Painel de Qualidade e Aviso no Card de Localização

- [x] 3.1 Escrever testes em `editor/core/avaliador_nota_qualidade_test.py`, `editor/views/widget_painel_qualidade_test.py` e `editor/views/widget_mensagem_coordenada_test.py` validando: (a) malha sincronizada com `versao < 2` concede `700/1000` pontos na tarefa `etapa1_malha_estrada_picos` com `concluida = False` (`pronto_para_publicar = False`, mantendo croquis já publicados com aviso de pendência) e ação `"Atualizar mapa de pontos"`; e (b) `WidgetMensagemCoordenada._atualizar_status_malha_pico` exibe aviso de versão desatualizada (`v0 → v2` / `v1 → v2`) quando `versao < 2` (Red)
- [x] 3.2 Implementar a avaliação de versão em `editor/core/avaliador_nota_qualidade.py` e o aviso de versão em `editor/views/widget_mensagem_coordenada.py`, garantindo 100% de cobertura com `pytest` (Green)
