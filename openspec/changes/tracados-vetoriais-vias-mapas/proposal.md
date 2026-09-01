# Proposta: Sistema de Traçados Vetoriais e Destaque Dinâmico de Vias em Mapas

## Why

Atualmente, os croquis do Aresta são majoritariamente baseados em digitalizações de guias legados em PDF com marcações raster já embutidas, onde os mapas apenas definem áreas simples (*Bounding Circles* ou *Retângulos*) para posicionar caixas de clique. Para a nova geração de croquis criados diretamente sobre fotos limpas de alta resolução, é essencial permitir o desenho vetorial completo das linhas de vias e boulders. Isso viabiliza a padronização visual moderna dos topos de escalada, suporta trechos compartilhados entre vias e variantes como um grafo semântico, e garante renderização acelerada por GPU com destaque contínuo no aplicativo móvel consumindo o mínimo de bateria.

## What Changes

- **Schema Protobuf & YAML (`croqui.proto`):**
  - Evolução do `PontoDeInteresse` / `ElementoVisual` para suportar `LinhaTrajeto` através do campo `linha`.
  - Separação estrita em `oneof representacao` entre a intenção semântica editável (`conteudo` com nós tipados `PASSAGEM`, `INICIO_BASE`, `INICIO_AGACHADO`, `PROTECAO_FIXA`, `PARADA_INTERMEDIARIA`, `TOP_PARADA`, `CRUX`) e o cache pré-computado para o aplicativo (`compilado` contendo `caminho_svg`, `caixa_delimitadora` e marcadores pré-posicionados).
  - Suporte completo a composição de referências: vias e variantes podem compartilhar trechos de linha comuns através da lista de `ids` em `Referencia`.
- **Biblioteca Matemática de Interpolação e Compilação (Library-First & TDD):**
  - Implementação da biblioteca matemática autônoma e pura (sem dependência de GUI) para calcular a Spline Centripetal Catmull-Rom e converter nós em Curvas de Bézier Cúbicas (formato padrão SVG Path `caminho_svg`).
  - Integração no pipeline de compilação (`build.py` / `scripts/deploy_generated.py`) para pré-calcular o `caminho_svg` e a `caixa_delimitadora` nos arquivos compilados (`.binarypb` e `compilado.yaml`).
- **Editor de Mapas Desktop (Integrado à QUndoStack):**
  - Nova ferramenta visual de desenho de linhas ("Nova Linha" / Caneta) no painel do editor de mapas.
  - Edição vetorial interativa de nós (movimentação com recálculo de spline em tempo real, menu de contexto para alternar tipos de nós, adição e remoção de pontos).
  - Todas as mutações de nós e linhas mediadas obrigatoriamente por comandos `QUndoCommand` na pilha global de histórico.
  - Suporte a *snapping* magnético ao conectar novos trechos de variantes a nós existentes.
- **Visualização e Interação (App Mobile / Serving):**
  - Renderização 100% acelerada por hardware via GPU (Impeller/Skia) a partir dos caminhos SVG pré-compilados.
  - Destaque contínuo (*highlight*) da via inteira selecionada com traçado de alto contraste, esmaecimento das vias inativas e enquadramento suave da câmera.

## Capabilities

### New Capabilities
- `tracados-vetoriais-mapas`: Modelo de dados, semântica de nós de escalada, biblioteca matemática de interpolação Spline Catmull-Rom para Bézier e pipeline de compilação em SVG Path GPU-ready.

### Modified Capabilities
- `editor-mapas`: Adição da ferramenta visual de caneta/traçado de vias, manipulação e movimentação interativa de nós com spline em tempo real, alternância de tipos de nó e suporte a histórico (undo/redo).

## Impact

- **Protobuf (`aresta_api/proto/croqui.proto`):** Adição de mensagens `LinhaTrajeto`, `DadosConteudoLinha`, `DadosCompiladosLinha`, `NoTrajeto`, `MarcadorCompilado`. Total retrocompatibilidade com campos existentes de `PontoDeInteresse`. Nomenclatura 100% em português brasileiro.
- **Core da Aplicação (`editor/core/` / `aresta_api/core/`):** Biblioteca pura de interpolação Spline e expansão de `GeometriaPOI` para suportar `LinhaTrajeto`.
- **Views do Editor (`editor/views/widget_editor_mapas.py`):** Novo item gráfico `ItemTrajetoLinha` e ferramenta de caneta com feedback em tempo real.
- **Compilador e Scripts (`build.py`, `scripts/`):** Atualização dos processos de geração de croquis compilados para preencher os dados de caminhos SVG.
