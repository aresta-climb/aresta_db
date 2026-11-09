# Design

## Context

Conforme detalhado em `proposal.md`, o uso prático da geração de malha rodoviária OSM na Gruta da Lapinha (Lagoa Santa/MG, limítrofe à Região Metropolitana de Belo Horizonte) revelou quatro necessidades de evolução arquitetural:
1. A execução síncrona de `construir_malha_estrada_pico_proto` na UI thread do Qt bloqueava o Editor durante toda a requisição Overpass + cálculo de Dijkstra.
2. A query Overpass buscava vias `residential`, `living_street`, `service` e `track` num raio de 15 km (`around:15000`), baixando a malha urbana residencial inteira de cidades vizinhas quando apenas o entorno imediato do pico precisa dessas vias para conectar o estacionamento à rede coletora.
3. Os ~630 nós de `MalhaEstradaPico` eram serializados inline em `database/<id>/croqui.yaml`, adicionando milhares de linhas ao arquivo principal do croqui.
4. O `exportar_catalogo_csv` em `scripts/gerar_catalogo_sqlite_lib.py` exportava apenas `catalogo_croquis.csv`, `catalogo_aresta.csv` e `catalogo_meta.csv`, omitindo `catalogo_nos_estrada.csv` e `catalogo_distancias_estrada.csv`.

## Goals / Non-Goals

**Goals:**
- Manter a UI do Editor 100% responsiva durante a geração do mapa de pontos, exibindo progresso detalhado e permitindo cancelamento.
- Reduzir em >80% o payload Overpass próximo a áreas metropolitanas mantendo a cobertura da grade de 3 anéis (`15 / 60 / 180 km`).
- Isolar a malha rodoviária em `database/<id>/malha_estrada.yaml` (ou `malha_estrada_<idx>.yaml`) usando o padrão `Arquivo*` do Protobuf (`ArquivoMalhaEstrada`).
- Garantir visibilidade em texto puro nos commits de `generated/` para `catalogo_nos_estrada.csv` e `catalogo_distancias_estrada.csv`.

**Non-Goals:**
- Alterar o esquema SQL de `catalogo.sql` ou o cálculo de distância no aplicativo Flutter (`aresta_app`).

## Decisions

### 1. Envelope `ArquivoMalhaEstrada` no `croqui.proto` e arquivo `malha_estrada.yaml`
- **Decisão**: Seguir o padrão canônico de arquivos filhos do projeto (`ArquivoMapas`, `ArquivoCuradoriaBetas`, `ArquivoSetor`, `ArquivoGrupo`) criando:
  ```protobuf
  message ArquivoMalhaEstrada {
    option (aresta.mensagem_formato_na_ui) = INVISIVEL;
    oneof arquivo {
      string caminho = 1;
      MalhaEstradaPico conteudo = 2;
    }
    extensions 1000 to max;
  }
  ```
  E alterando o campo `15` de `Pico` para `ArquivoMalhaEstrada malha_estrada = 15 [(aresta.formato_na_ui) = INVISIVEL];`.
- **Comportamento no Editor (`CroquiModel`) e Pipeline (`preparar_submissao_lib.py`)**:
  - `CroquiModel.carregar_do_disco`: quando `pico.malha_estrada` possui `caminho` (ou quando `malha_estrada.yaml` existe), carrega o YAML do disco e preenche `pico.malha_estrada.conteudo`.
  - `CroquiModel.extrair_arquivos_e_serializar`: quando `pico.malha_estrada.conteudo.pontos` não está vazio, serializa o conteúdo de `MalhaEstradaPico` para `malha_estrada.yaml` (para o primeiro pico, ou `malha_estrada_<idx>.yaml` para picos adicionais) com cabeçalho SPDX ODbL-1.0 e substitui no `croqui.yaml` por `malha_estrada: { caminho: "malha_estrada.yaml" }`.
  - `compilar_croqui`: expande `pico["malha_estrada"]["caminho"]` lendo o YAML do disco para `pico["malha_estrada"] = {"conteudo": ...}` antes de serializar o `compilado.binarypb`.
  - `coletar_referencias_arquivos` / `limpar_arquivos_nao_utilizados` / `corrigir_database`: reconhece referências `caminho` terminadas em `.yaml` para preservar `malha_estrada.yaml` e validar seu cabeçalho SPDX.

### 2. Micro-anel de 4 km para vias de acesso local na Overpass API
- **Decisão**: Dividir a busca do Anel 1 em `construir_query_overpass`:
  - **Acesso Local (`0–4 km`, `around:4000`)**: `residential|living_street|service|track` (garante a conexão de trilhas, estradas de terra e ruas locais do estacionamento até a via coletora mais próxima).
  - **Anel 1 (`0–15 km`, `around:15000`)**: `motorway| motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|unclassified`.
  - **Anel 2 (`15–60 km`, `around:60000`)**: `motorway..tertiary_link`.
  - **Anel 3 (`60–180 km`, `around:180000`)**: `motorway..secondary_link`.
- **Racional**: Em qualquer rodovia de aproximação a mais de 4 km do estacionamento do pico, o trajeto já trafega por vias coletoras/rodovias (`unclassified` ou superior). Evitar o download de todas as ruas `residential` e `service` num raio de 15 km impede que cidades vizinhas inteiras inflacionem o JSON da Overpass e o grafo do Dijkstra.

### 3. Execução Assíncrona com `QThread` e `DialogoProgressoMalhaEstrada`
- **Decisão**:
  - Adicionar parâmetros opcionais `ao_progresso: Callable[[str, int], None] | None = None` e `verificador_cancelamento: Callable[[], bool] | None = None` em `construir_malha_estrada_pico_proto` (e `consultar_overpass_grafo`), levantando ` ErroMalhaEstradaCancelada` se o cancelamento for solicitado.
  - Em `editor/views/inspector/widget_mensagem_coordenada.py`, criar `WorkerGeracaoMalhaEstrada(QThread)` e `DialogoProgressoMalhaEstrada(QDialog)` exibindo barra de progresso (`0–100%`), lista/log das etapas concluídas e botão `Cancelar`.
  - Para manter determinismo em testes unitários sem abrir loops bloqueantes desnecessários quando um `gerador_malha` customizado síncrono é injetado ou através do diálogo testável, o diálogo e o worker expõem sinais claros (`progresso_alterado`, `concluido_com_sucesso`, `falhou`).

### 4. Exportação de `catalogo_nos_estrada.csv` e `catalogo_distancias_estrada.csv`
- **Decisão**: Atualizar `exportar_catalogo_csv` em `scripts/gerar_catalogo_sqlite_lib.py` para verificar e exportar os 5 arquivos CSV:
  - `catalogo_croquis.csv`
  - `catalogo_aresta.csv`
  - `catalogo_nos_estrada.csv` (`SELECT no_osm_id, latitude_e7, longitude_e7 FROM catalogo_nos_estrada ORDER BY no_osm_id ASC`)
  - `catalogo_distancias_estrada.csv` (`SELECT croqui_uid, no_osm_id, distancia_metros, na_borda FROM catalogo_distancias_estrada ORDER BY croqui_uid ASC, no_osm_id ASC`)
  - `catalogo_meta.csv`

## Risks / Trade-offs

- **[Risk] Cancelamento durante requisição HTTP bloqueante (`urlopen`)** → **Mitigação**: Ao clicar em `Cancelar`, o diálogo marca a flag de cancelamento cooperativo no worker, desconecta a aplicação do resultado e fecha imediatamente a janela para que o usuário nunca fique bloqueado esperando o socket fechar.
- **[Risk] Croquis que já tenham `malha_estrada` inline no `croqui.yaml`** → **Mitigação**: Se `pico.malha_estrada` vier com `conteudo` direto (ou formato plano legado), `CroquiModel` e `compilar_croqui` aceitam normalmente e, no próximo salvamento, extraem para `malha_estrada.yaml`.
