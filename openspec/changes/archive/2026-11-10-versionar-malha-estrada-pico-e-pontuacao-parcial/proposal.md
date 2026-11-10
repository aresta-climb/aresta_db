# Proposal

## Why

Sempre que o algoritmo de geração da malha rodoviária evolui (como a inclusão de `duracao_minutos` e o ajuste do Anel 3 para `150 km` / `200 km` por estrada), os arquivos `malha_estrada.yaml` já gerados continuam com a coordenada sincronizada, mas foram gerados por uma versão anterior do algoritmo. Adicionar um campo `int32 versao = 4` em `MalhaEstradaPico` com a versão atual hardcoded (`VERSAO_ATUAL_MALHA_ESTRADA = 2`) permite detectar automaticamente malhas de versões anteriores, concedendo pontuação parcial (`700/1000` pontos, `concluida = False`) no Painel de Qualidade e exibindo aviso explícito para atualização no campo de localização do pico, sem remover os dados existentes do catálogo até que o autor regere a malha.

## What Changes

- **Contrato Protobuf (`aresta_api/proto/croqui.proto`)**:
  - Adicionar `int32 versao = 4;` na mensagem `MalhaEstradaPico` e recompilar os bindings Protobuf (`build.py`).
- **Versionamento da malha (`scripts/gerar_malha_estrada_lib.py`)**:
  - Definir `VERSAO_ATUAL_MALHA_ESTRADA = 2` e preencher `versao=VERSAO_ATUAL_MALHA_ESTRADA` em `construir_malha_estrada_pico_proto`.
  - Distinguir `malha_estrada_pico_sincronizada(pico)` (coordenada bate e nós com `distancia_metros > 0` possuem `duracao_minutos > 0`, usada por `extrair_linhas_malha_de_pico_proto` para não perder os pontos no catálogo offline) de `malha_estrada_pico_atualizada(pico)` (que exige adicionalmente `versao >= VERSAO_ATUAL_MALHA_ESTRADA`).
- **Pontuação parcial (`700/1000` pts) na tarefa 1.8 do Painel de Qualidade (`editor/core/avaliador_nota_qualidade.py`)**:
  - Quando a malha de um pico está sincronizada com a coordenada e possui `duracao_minutos`, mas tem `versao < VERSAO_ATUAL_MALHA_ESTRADA`, conceder `0.7` do peso do pico (`700` de `1000` pontos em croqui de pico único), manter `concluida = False` (bloqueando `pronto_para_publicar` para novos rascunhos, enquanto croquis já publicados permanecem publicados exibindo o aviso de pendência) e emitir a ação `"Atualizar mapa de pontos"`.
- **Aviso de versão desatualizada no Card de Localização (`editor/views/widget_mensagem_coordenada.py`)**:
  - Exibir `⚠️ Mapa de pontos de estrada desatualizado (v<atual> → v2). Clique em Gerar Mapa de Pontos para atualizar.` quando a malha estiver sincronizada, porém em versão anterior a `VERSAO_ATUAL_MALHA_ESTRADA`.

## Capabilities

### New Capabilities
- *(Nenhuma nova capability)*

### Modified Capabilities
- `malha-estrada-osm-precomputada`: Adiciona `versao = 4` em `MalhaEstradaPico` (`VERSAO_ATUAL_MALHA_ESTRADA = 2`), mantendo a exportação do catálogo para malhas sincronizadas e exigindo `versao >= 2` para considerar a malha atualizada.
- `painel-nota-qualidade-croqui`: Concede pontuação parcial (`700/1000` pontos) com `concluida = False` na tarefa `etapa1_malha_estrada_picos` quando o mapa de pontos do pico possui versão inferior a `VERSAO_ATUAL_MALHA_ESTRADA`.

## Impact

- **`aresta_api`**: `proto/croqui.proto` e artefatos gerados.
- **`aresta_db`**: `scripts/gerar_malha_estrada_lib.py`, `editor/core/avaliador_nota_qualidade.py`, `editor/views/widget_mensagem_coordenada.py` e respectivos testes.
