# Proposal

## Why

Atualmente, a geração da malha rodoviária do OpenStreetMap (Overpass API) estava acoplada opcionalmente à etapa de compilação do catálogo (`gerar_catalogo_completo`), o que traz dois problemas arquiteturais: (1) os workflows de CI/CD (`pr-integrator.yml` e `pr-db-validator.yml`) e o comando `deploy_generated.py --force` precisam ser 100% offline, rápidos e imunes a bloqueios/timeouts de rede ou rate-limits da Overpass API em IPs de data center; e (2) se a malha viver apenas no artefato derivado `generated/catalogo.db`, qualquer reconstrução limpa (`--force`) ou alteração de coordenadas de um pico perde ou congela a malha antiga. Mover a geração da malha OSM para o momento de edição da localização do `Pico` no Editor Desktop e persistir o resultado pré-computado em `database/<id>/croqui.yaml` garante compilação 100% offline, detecção exata de mudança de coordenada e feedback visual imediato para o curador.

## What Changes

- **Persistência Pré-computada no Modelo do Pico (`aresta_api` / `database/<id>/croqui.yaml`)**:
  - Adicionar as mensagens `NoMalhaEstrada` e `MalhaEstradaPico` (`latitude_referencia_e7`, `longitude_referencia_e7`, `repeated NoMalhaEstrada nos`) em `aresta_api/proto/croqui.proto` e o campo `MalhaEstradaPico malha_estrada` em `Pico` (oculto na árvore via `INVISIVEL`).
- **Geração no Editor Desktop Exclusivamente em `Pico.localizacao`**:
  - Estender `WidgetMensagemCoordenada` para que, exclusivamente quando vinculado à localização de um `Pico`, exiba o status da malha rodoviária (warning `⚠️ Mapa de pontos de estrada não gerado para esta localização` quando ausente ou defasado em relação à coordenada atual) e um botão ao lado (`Gerar Mapa de Pontos`) para consultar a Overpass API.
  - Atualizar automaticamente a malha ao editar/colar coordenadas válidas em `Pico.localizacao` (ou ao acionar o botão), registrando a mutação via comando no histórico Undo/Redo e degradando graciosamente sem bloquear a edição caso o usuário esteja sem internet.
  - Garantir que todas as demais ocorrências de `Coordenada` (`Setor`, `Grupo`, `PontoDeInteresse`) não exibam o botão nem o aviso de malha.
- **Resiliência e Failover de Espelhos no `ClienteOverpass`**:
  - Configurar `ClienteOverpass` com cabeçalho `User-Agent` identificável do projeto e failover automático entre múltiplos espelhos públicos oficiais da Overpass API (`overpass-api.de`, `overpass.private.coffee`, `maps.mail.ru/osm/tools/overpass`).
- **Compilação 100% Offline e Warning de Compilação**:
  - Em `scripts/deploy_generated.py`, emitir um `Aviso:` não-bloqueante quando um `Pico` possuir `localizacao` válida mas não tiver `malha_estrada` gerada para aquela coordenada.
  - Em `scripts/gerar_catalogo_sqlite_lib.py`, alimentar `catalogo_nos_estrada` e `catalogo_distancias_estrada` de forma 100% offline diretamente a partir de `croqui.picos[0].malha_estrada` do `compilado.binarypb` (quando sincronizada com a coordenada atual do pico), permitindo que `deploy_generated.py --force` e `pr-integrator.yml` reconstruam `catalogo.db` integralmente sem acesso à rede.

## Capabilities

### New Capabilities

### Modified Capabilities
- `malha-estrada-osm-precomputada`: Atualiza o ciclo de vida da malha rodoviária para persistir os nós e a coordenada de referência no modelo `Pico` (`database/<id>/croqui.yaml`) e adiciona failover entre espelhos públicos da Overpass API.
- `editor-campo-coordenada-e7`: Adiciona o indicador de aviso e o botão de geração da malha de pontos do OpenStreetMap exclusivamente na edição de `Pico.localizacao`, além da atualização automática ao alterar a coordenada do pico.
- `catalogo-sqlite-delta-sync`: Torna a população de `catalogo_nos_estrada` e `catalogo_distancias_estrada` 100% offline a partir do `compilado.binarypb` e emite aviso de compilação quando a malha do pico estiver ausente ou desatualizada.

## Impact

- **`aresta_api`**: `proto/croqui.proto` e stubs Python/Dart gerados.
- **`aresta_db` (`editor/`)**: `editor/views/widget_mensagem_coordenada.py`, `editor/views/widget_editor_dados.py` e respectivos testes.
- **`aresta_db` (`scripts/`)**: `scripts/gerar_malha_estrada_lib.py`, `scripts/gerar_catalogo_sqlite_lib.py`, `scripts/deploy_generated.py` e respectivos testes.
