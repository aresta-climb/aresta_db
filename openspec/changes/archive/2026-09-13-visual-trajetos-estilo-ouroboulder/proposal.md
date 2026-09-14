# Proposta: Estilização Visual de Traçados e Marcadores no Padrão Ouroboulder

## Why

Os traçados vetoriais automáticos gerados pelo editor e renderizados no aplicativo móvel apresentam atualmente círculos com bordas brancas espessas, tipografia pequena espremida e preenchimento colorido permanente, o que sobrecarrega a visualização do croqui e impede o efeito de destaque (*highlight*) limpo observado no croqui de referência Ouroboulder. Esta mudança padroniza a cor padrão das linhas para amarelo fluorescente de alto contraste, elimina a borda branca dos círculos adotando fundo preto neutro com ativação colorida na via selecionada, amplia os rótulos tipográficos e introduz nós com setas direcionais de movimento/dinâmico, sincronizando com fidelidade estética 1:1 o Editor e o App.

## What Changes

- **Cor Padrão de Traçado**: Alterar a cor padrão de novas linhas de traçado de laranja (`#FF6D00`) para amarelo (`#FFD600` / `#FFEB3B`), proporcionando máxima visibilidade e contraste luminoso sobre texturas escuras e sombras de rocha.
- **Redesenho dos Círculos de Marcação (Badges)**:
  - Eliminar a borda branca grossa interna (`strokeWidth = 1.5 - 2.0`) em círculos identificadores (`CIRCULO_IDENTIFICADOR`, `INICIO_AGACHADO`, `FIM_TOP`).
  - Adotar contorno preto fino e sutil (1.0px) de alto contraste idêntico à sombra das linhas tracejadas.
  - Em estado de repouso (não selecionado), exibir o fundo do círculo em preto neutro (`#1A1A1A` / 90% opacidade) com texto branco.
  - Em estado ativo (via selecionada), preencher o círculo com a cor de destaque da via (amarelo ou cor personalizada) com halo luminoso.
  - Ampliar a escala tipográfica dos rótulos internos para preencher confortavelmente 75% a 80% do diâmetro útil do círculo, com peso negrito extra para leitura à distância sob sol pleno.
- **Novo Tipo de Nó no Protobuf e Editor: Seta Direcional (`SETA_DIRECIONAL`)**:
  - Adicionar o enum `SETA_DIRECIONAL = 12` em `NoTrajeto.TipoNo` em `aresta_api/proto/croqui.proto`.
  - Permitir a marcação de nós intermediários com setas orientadas pela tangente da curva spline para indicar dinâmicos, botes e sentidos de travessia (ex: boulder Manobra).
  - Pré-computar e compilar a orientação do marcador no pipeline (`MarcadorCompilado`).
- **Sincronização 1:1 entre Editor e Aplicativo Móvel**:
  - Implementar o mesmo comportamento de renderização em `editor/views/widget_editor_mapas.py` (`AlcaNoTrajeto`) e `aresta_app/frontend/lib/pages/mapa_interativo.dart` (`MarkerPainter`).

## Capabilities

### Modified Capabilities
- `tracados-vetoriais-mapas`: Atualização dos requisitos de estilo de marcadores circulares (fundo preto neutro vs. highlight ativo, eliminação da borda branca espessa, tipografia proporcional ampliada), cor padrão amarela e suporte ao novo tipo semântico de nó `SETA_DIRECIONAL`.

## Impact

- **Modelos e Protobuf**: `aresta_api/proto/croqui.proto` (novo enum `SETA_DIRECIONAL`), recompilação de stubs Python (`croqui_pb2.py`) e Dart (`croqui.pb.dart`).
- **Editor Desktop (Aresta DB)**: `editor/views/widget_editor_mapas.py` (`AlcaNoTrajeto`, `ItemTrajetoLinha`, criação de novas linhas com cor padrão amarela, menu de contexto de nós com opção Seta Direcional), `editor/core/spline_catmull_rom.py` e testes unitários.
- **Pipeline de Compilação**: `scripts/preparar_submissao_lib.py` atualizado para tratar o ângulo e tipo de `SETA_DIRECIONAL` nos marcadores compilados.
- **Aplicativo Móvel (Aresta App)**: `aresta_app/frontend/lib/pages/mapa_interativo.dart` (`MarkerPainter`) atualizado para desenhar badges pretos em repouso, highlight na cor da via selecionada e suporte a setas direcionais.
