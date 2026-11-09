# Proposal

## Why

Ao gerar o mapa de pontos rodoviários no Editor Aresta (especialmente em picos próximos a regiões metropolitanas como a Gruta da Lapinha), a execução síncrona na thread principal congelava a interface por mais de 30 segundos (devido à busca de vias `residential`/`service` num raio urbano de 15 km), gravava centenas de nós diretamente dentro do `croqui.yaml` poluindo o arquivo principal e não exportava as tabelas da malha rodoviária em `.csv` na pasta `generated/` para visibilidade nos commits.

## What Changes

- **Janela de Progresso em Background no Editor (`QThread` + `DialogoProgressoMalhaEstrada`)**: A geração do mapa de pontos passa a rodar em background fora da thread de UI, exibindo um diálogo modal com barra de progresso, etapas detalhadas em tempo real (conexão Overpass, filtragem de componente conexo, cálculo Dijkstra e amostragem nos 3 anéis) e botão **Cancelar**.
- **Otimização da Consulta Overpass em Regiões Urbanas**: Restringe a busca de vias locais (`residential`, `living_street`, `service`, `track`) a um micro-anel de **4 km** ao redor do estacionamento do pico (suficiente para conectar o acesso local à malha coletora) e mantém o Anel 1 (`15 km`) com vias de `unclassified` até `motorway`, reduzindo drasticamente o volume de dados e o tempo de geração perto de grandes cidades sem perder cobertura na grade de 2,2 km.
- **BREAKING (Contrato Protobuf / YAML) — Isolamento em Arquivo Separado `malha_estrada.yaml` via `ArquivoMalhaEstrada`**: Introduz a mensagem envelope `ArquivoMalhaEstrada` (`oneof arquivo { string caminho = 1; MalhaEstradaPico conteudo = 2; }`) no campo `Pico.malha_estrada = 15`. No `database/<id>/croqui.yaml` fica apenas a referência `malha_estrada: { caminho: malha_estrada.yaml }`, enquanto os pontos ficam isolados em `database/<id>/malha_estrada.yaml` (com cabeçalho SPDX ODbL-1.0) e são expandidos em `conteudo` na compilação do `compilado.binarypb`.
- **Exportação de `catalogo_nos_estrada.csv` e `catalogo_distancias_estrada.csv`**: Atualiza `exportar_catalogo_csv` para exportar também as duas tabelas da malha rodoviária em `generated/catalogo_nos_estrada.csv` e `generated/catalogo_distancias_estrada.csv`, garantindo visibilidade completa das alterações de malha nos diffs do Git.

## Capabilities

### New Capabilities

### Modified Capabilities
- `malha-estrada-osm-precomputada`: Otimiza a query Overpass com micro-anel de 4 km para vias locais, adiciona callback de progresso/cancelamento e altera `Pico.malha_estrada` para o envelope `ArquivoMalhaEstrada` persistido em `malha_estrada.yaml` separado e expandido no `compilado.binarypb`.
- `editor-campo-coordenada-e7`: Executa a geração da malha rodoviária em background (`QThread`) com janela modal de progresso (`DialogoProgressoMalhaEstrada`) e suporte a cancelamento sem congelar a interface do Editor.
- `catalogo-sqlite-delta-sync`: Estende a exportação incremental determinística do catálogo em CSV para incluir `catalogo_nos_estrada.csv` e `catalogo_distancias_estrada.csv`.

## Impact

- **`aresta_api` (`proto/croqui.proto`)**: Adição de `ArquivoMalhaEstrada` e atualização do tipo de `Pico.malha_estrada = 15` para `ArquivoMalhaEstrada` (regenerando stubs Python e Dart).
- **`aresta_db/scripts/gerar_malha_estrada_lib.py`**: Otimização de `construir_query_overpass` (micro-anel de 4 km para vias locais) e suporte a callbacks de progresso e cancelamento em `construir_malha_estrada_pico_proto`.
- **`aresta_db/editor/views/inspector/widget_mensagem_coordenada.py`**: Adição de `WorkerGeracaoMalhaEstrada(QThread)` e `DialogoProgressoMalhaEstrada(QDialog)`, além da leitura/escrita via `pico.malha_estrada.conteudo`.
- **`aresta_db/editor/models/croqui_model.py` e `aresta_db/scripts/preparar_submissao_lib.py`**: Hidratação, serialização separada em `malha_estrada.yaml`, preservação na limpeza de órfãos/SPDX e expansão em `compilar_croqui`.
- **`aresta_db/scripts/gerar_catalogo_sqlite_lib.py`**: Leitura de `pico.malha_estrada.conteudo` e exportação determinística de `catalogo_nos_estrada.csv` e `catalogo_distancias_estrada.csv` em `exportar_catalogo_csv`.
