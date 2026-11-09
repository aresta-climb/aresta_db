# Design

## Context

Conforme detalhado em `proposal.md`, o pipeline de compilação (`scripts/deploy_generated.py`) é executado tanto a cada salvamento no Editor Desktop quanto nos workflows de CI (`pr-db-validator.yml` e `pr-integrator.yml`). Para que a compilação seja instantânea, determinística, 100% offline e capaz de reconstruir `generated/` do zero com `--force`, a consulta à Overpass API (OpenStreetMap) deve acontecer no momento em que a coordenada do `Pico` é editada no Editor Desktop (ou via botão dedicado na UI do `Pico`), persistindo os pontos pré-computados diretamente em `database/<id>/croqui.yaml`.

## Goals / Non-Goals

**Goals:**
- Persistir a malha rodoviária pré-computada dentro da mensagem `Pico` (`aresta_api/proto/croqui.proto`), garantindo serialização automática em `database/<id>/croqui.yaml` e `generated/<id>/compilado.binarypb`.
- Detectar de forma determinística se a malha de um `Pico` está sincronizada com sua `localizacao` atual comparando `(latitude_referencia_e7, longitude_referencia_e7)` com `(localizacao.latitude, localizacao.longitude)`.
- Adicionar ao `WidgetMensagemCoordenada` — exclusivamente quando vinculado a `Pico.localizacao` — um aviso visual quando a malha estiver ausente/defasada e um botão `Gerar Mapa de Pontos` (além de disparar a atualização ao editar/colar coordenadas válidas no `Pico`).
- Dotar `ClienteOverpass` de failover automático entre múltiplos espelhos públicos oficiais da Overpass API.
- Tornar `deploy_generated.py` e `gerar_catalogo_completo()` 100% offline por padrão, extraindo a malha diretamente de `croqui.picos[0].malha_estrada` do `compilado.binarypb` e emitindo `Aviso:` não-bloqueante quando um `Pico` com localização não tiver malha atualizada.

**Non-Goals:**
- Exibir botão ou aviso de malha rodoviária em coordenadas de `Setor`, `Grupo` ou `PontoDeInteresse`.
- Bloquear o salvamento no Editor ou falhar o CI caso o autor edite um croqui sem conexão com a internet (nesses casos, o warning é exibido e o aplicativo móvel utiliza o fallback `Haversine * 1.3`).

## Decisions

### 1. Modelagem no Protobuf (`Pico.malha_estrada`)
- **Decisão**: Definir `NoMalhaEstrada` e `MalhaEstradaPico` em `aresta_api/proto/croqui.proto` com `option (aresta.mensagem_formato_na_ui) = INVISIVEL;` e adicionar `MalhaEstradaPico malha_estrada = 15 [(aresta.formato_na_ui) = INVISIVEL];` em `Pico`.
- **Racional**: Todo o ciclo de vida do Editor Desktop (`CroquiModel.carregar_do_disco`, `CroquiModel.salvar_para_disco`, comandos `CmdAlterarCampo` com Undo/Redo e compilação em memória via `usar_contexto_memoria_deploy`) opera nativamente sobre a árvore Protobuf do `Croqui`. Guardar `malha_estrada` em `Pico` elimina a necessidade de arquivos paralelos fora do padrão Protobuf e permite que `gerar_catalogo_completo()` leia tudo diretamente do `compilado.binarypb` já aberto no loop de geração do `catalogo.db`.

### 2. Escopo Exclusivo em `Pico.localizacao` no `WidgetMensagemCoordenada`
- **Decisão**: O `WidgetMensagemCoordenada` receberá um parâmetro opcional `msg_pico: Any | None = None` (preenchido por `WidgetEditorDados._render_field_inner` apenas quando `msg.DESCRIPTOR.name == "Pico"` e `field.name == "localizacao"`).
- **Racional**: Outras mensagens (`Setor`, `Grupo`, `PontoDeInteresse`) também utilizam `Coordenada` (`MensagemFormatoUi.COORDENADA`). Restringir a passagem de `msg_pico` a `Pico.localizacao` garante que todas as demais telas de coordenadas permaneçam inalteradas (apenas botões `Colar` e `Abrir no Maps`).

### 3. Failover de Espelhos Públicos no `ClienteOverpass`
- **Decisão**: `ClienteOverpass` terá como lista padrão de endpoints:
  1. `https://overpass-api.de/api/interpreter`
  2. `https://overpass.private.coffee/api/interpreter`
  3. `https://maps.mail.ru/osm/tools/overpass/api/interpreter`
  Com `User-Agent: ArestaClimbEditor/1.0 (+https://arestaclimb.com)`. Se um endpoint lançar `URLError`, `HTTPError` ou `TimeoutError`, o cliente tenta o próximo antes de propagar a exceção.
- **Racional**: A Overpass API não utiliza API Keys; a resiliência contra indisponibilidade momentânea de uma instância é alcançada combinando `User-Agent` identificável, requisições originadas do IP do usuário no Editor Desktop e failover entre os espelhos públicos oficiais.

### 4. Compilação 100% Offline e Warning de Compilação
- **Decisão**:
  - Em `scripts/deploy_generated.py`, adicionar `verificar_malha_estrada_pico(croqui_id, croqui_compilado)` no Passo A para emitir `Aviso: O pico '<nome>' no croqui '<id>' está sem mapa de pontos de estrada atualizado para sua localização.` quando `localizacao` for válida mas `malha_estrada` estiver ausente ou com coordenada de referência divergente.
  - Em `scripts/gerar_catalogo_sqlite_lib.py`, ler `croqui.picos[0].malha_estrada` diretamente do `compilado.binarypb` (quando sincronizada com `croqui.picos[0].localizacao`) e atualizar `catalogo_nos_estrada` e `catalogo_distancias_estrada` de forma 100% offline (mantendo suporte opcional a `cliente_overpass` apenas para utilitários de linha de comando/migração em lote).
  - Em `.github/workflows/deploy.yml`, adicionar `scripts/gerar_malha_estrada_lib.py` ao `sparse-checkout` para garantir que todos os módulos importados por `gerar_catalogo_sqlite_lib.py` estejam presentes no job de deploy.

## Risks / Trade-offs

- **[Risco] Pequena latência de rede (2–5s) ao consultar a Overpass API no Editor Desktop** → **Mitigação**: Se a chamada à Overpass falhar ou o usuário estiver offline, capturar a exceção sem travar o editor, mantendo o warning e o botão `Gerar Mapa de Pontos` visíveis para que o usuário possa regerar quando desejar.
- **[Risco] Coordenada do pico editada manualmente no `croqui.yaml` sem atualizar `malha_estrada`** → **Mitigação**: Como `malha_estrada` armazena `latitude_referencia_e7` e `longitude_referencia_e7`, tanto o Editor Desktop quanto `deploy_generated.py` e `gerar_catalogo_completo()` detectam imediatamente a divergência, emitem `Aviso:` e evitam publicar distâncias de uma coordenada antiga no `catalogo.db`.
