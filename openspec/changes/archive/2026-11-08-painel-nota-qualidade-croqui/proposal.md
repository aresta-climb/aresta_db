# Proposal

## Why

Atualmente, ao abrir um croqui no Editor Aresta, o autor cai diretamente na árvore estrutural de dados (`PaginaDados`), sem uma visão consolidada do quão completo o croqui está ou de quais passos faltam para torná-lo pronto para publicação e excelente para uso em campo. Além disso, o `indice.binarypb` não possui um sinal quantitativo da qualidade e completude de cada croqui (`nota_qualidade`) que permita ao aplicativo móvel priorizar e ordenar croquis mais completos ao lado do critério de distância geográfica.

## What Changes

- **Motor de Avaliação de `nota_qualidade` e Tarefas (Library-First)**: Criação de uma biblioteca independente e determinística (`editor/core/avaliador_nota_qualidade.py`) capaz de avaliar uma instância de `Croqui` (Protobuf ou dicionário em memória) e calcular a `nota_qualidade` em uma escala aberta aditiva estruturada em 3 etapas por ordens de grandeza:
  - **Etapa 1 — Essenciais para Publicação (`1000` pontos por critério)**: Identidade e capa (`caminho_thumbnail`), localização e link do Google Maps dos picos, instruções de chegada/acesso, Mapa Geral referenciando $>90\%$ dos setores/grupos (concedido automaticamente se houver apenas 1 setor), $>90\%$ dos setores com mapa, $>90\%$ das escaladas referenciadas em mapas, e $>90\%$ das escaladas com grau de dificuldade (incluindo `PROJETO` em vias e boulders).
  - **Etapa 2 — Qualidade, Navegação Offline e Segurança (`100` pontos por critério)**: Coordenadas de estacionamento e parede em $>90\%$ dos setores/grupos, trilhas de aproximação cadastradas, ficha técnica de extensão e proteções em $>90\%$ das vias encordadas (aplicabilidade automática se o croqui não tiver vias encordadas), traçados vetoriais (`LinhaTrajeto`) ou desenhos extraídos nos mapas, escaladas de destaque marcadas nos setores, descrições/betas textuais em pelo menos 50% das escaladas, e fotos de capa nos setores/grupos.
  - **Etapa 3 — Lapidação, História e Comunidade (`10` pontos por critério)**: Créditos do croqui, conquistadores e data de abertura nas escaladas, tipo de parede e exposição, indicadores de sinal de celular e adequação a crianças/bebês nos setores, vídeos de beta e ausência de `betas_pendentes`, dados de associação/Pix de manutenção, e flags de revisão (`revisado_manualmente` / `revisado_bounding_circle`).
- **Pontuação Parcial e Regra de Aplicabilidade Automática**: Critérios baseados em proporção (ex: meta de $90\%$) concedem pontuação parcial linear proporcional ao progresso atual até atingir $100\%$ dos pontos na meta ($\ge 90\%$), garantindo feedback imediato a cada edição. Critérios inaplicáveis à natureza do croqui (ex: Mapa Geral em croqui de 1 único setor, ou extensão/costuras em croqui exclusivo de Boulders) recebem $100\%$ dos seus pontos automaticamente.
- **Adição de `PROJETO` em `GrauBoulder`**: Inclusão do valor `PROJETO` no enum `GrauBoulder` em `croqui.proto` para paridade com `GrauVia`.
- **Nova Página Primária "Painel" no Editor (`PaginaPainel` / `WidgetPainelQualidade`)**:
  - Torna-se a primeira aba da barra lateral esquerda (índice 0, antes de `Dados`) e a visão aberta por padrão ao carregar um croqui na `JanelaPrincipal`.
  - Inspirada no painel de pré-lançamento do Google Play Console: exibe o cabeçalho com a `nota_qualidade` total, o status de publicação (`Rascunho` vs. `Publicado`) e as 3 etapas em seções colapsáveis (expandos) que se abrem em cascata (concluir $100\%$ da Etapa 1 recolhe a Etapa 1 e expande automaticamente a Etapa 2; concluir a Etapa 2 recolhe e expande a Etapa 3).
  - Exibe quanto cada tarefa pendente adicionará à `nota_qualidade` (ex: `+550 pts`) e fornece botões de ação rápida que navegam diretamente para o elemento ou mapa alvo utilizando `ContextoUIPath` (`foco_requisitado`).
  - Governa o controle client-side de `publicar_croqui` via comando de histórico (`QUndoCommand`): croquis em rascunho só habilitam a transição para `Publicado` ao atingir $100\%$ da Etapa 1 (croquis legados já publicados com pendências exibem alerta de regularização sem despublicação forçada, e o envio de Pull Request via `Propor Mudança` permanece livre mesmo em rascunho).
- **Persistência de `nota_qualidade` no `indice.binarypb`**:
  - Adição do campo `int32 nota_qualidade = 10;` em `PrecomputadosResumoCroqui` no arquivo `aresta_api/proto/indice.proto`.
  - Injeção automática de `precomputados.nota_qualidade` durante a compilação do índice em `scripts/deploy_generated.py` (refletindo tanto em `indice.binarypb` quanto em `indice.yaml`) e exibição da coluna `Nota Qualidade` no relatório `STATUS_CROQUIS.md` (`scripts/medir_saude_croquis.py`).

## Capabilities

### New Capabilities
- `painel-nota-qualidade-croqui`: Cálculo determinístico da `nota_qualidade` (escala aberta 1000/100/10 com pontuação parcial e aplicabilidade automática por modalidade), persistência em `PrecomputadosResumoCroqui.nota_qualidade` no `indice.binarypb` e interface da página primária "Painel" no Editor Aresta com etapas em cascata, navegação direta por contexto e portão client-side para o status `publicar_croqui`.

### Modified Capabilities
- `editor-area-principal`: A página "Painel" passa a ser a primeira visão da barra lateral esquerda (índice 0, com ícone dedicado) e a visualização inicial padrão ao abrir um croqui na `JanelaPrincipal`.

## Impact

- **Schemas Protobuf (`aresta_api/proto/`)**: `indice.proto` (`PrecomputadosResumoCroqui.nota_qualidade`) e `croqui.proto` (`GrauBoulder.PROJETO`).
- **Core e MVC do Editor (`editor/`)**:
  - `editor/core/avaliador_nota_qualidade.py` (e `avaliador_nota_qualidade_test.py`)
  - `editor/views/widget_painel_qualidade.py` (e `widget_painel_qualidade_test.py`)
  - `editor/legacy_views/area_principal.py` (integração da `PaginaPainel` no índice 0 e roteamento de foco)
  - `editor/views/estilo.py` (ícone `painel`)
- **Pipeline de Compilação e Saúde (`scripts/`)**:
  - `scripts/deploy_generated.py` (cálculo e gravação de `precomputados.nota_qualidade` no índice)
  - `scripts/medir_saude_croquis.py` (inclusão da nota de qualidade no relatório de saúde)
