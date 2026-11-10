# Proposal

## Why

Clicar individualmente em **Aprovar** ou **Rejeitar** um card na aba **Betas** ainda leva cerca de `3 segundos` (`~3030 ms` na Gruta da Lapinha) porque `PainelCuradoria.atualizar_visualizacao()` reconstrói todos os cards do zero com `QLabel(wordWrap=True)` e folhas CSS individuais por widget, `ProvedorImagemAresta` decodifica JPEGs a cada chamada, `CroquiController` aciona varredura $O(N)$ na árvore Protobuf e abas ocultas (`WidgetPainelQualidade`, `WidgetEditorDados`) reprocessam o modelo inteiro a cada clique. Além disso, o avaliador de qualidade ainda checava o arquivo legado `betas_pendentes.binarypb` na Etapa 3 (`10 pts`), marcando "Vídeos de beta e curadoria em dia" como concluído mesmo com dezenas de candidatos pendentes em `curadoria_betas`.

## What Changes

- **Otimização Sub-8ms (`< 8 ms`) na 1ª Abertura da Aba Betas e nas Ações Individuais de Curadoria**:
  - Reconciliação incremental e construção progressiva em fatias (*time-sliced*, `TAMANHO_FATIA_CARDS_PADRAO = 5`) de cards em `PainelCuradoria`: instanciar no frame inicial apenas a primeira fatia visível no topo do viewport e agendar as fatias seguintes via `QTimer.singleShot`, além de reutilizar/atualizar instâncias de `CardBetaCuradoria` existentes ao aprovar, rejeitar ou restaurar itens sem destruir e recriar os demais cards da lista.
  - Eliminar o gargalo de layout C++ do Qt (`2.59 s` em `processEvents`) removendo `setWordWrap(True)` patológico dos rótulos internos dos cards, definindo altura fixa consistente nos cards e centralizando o CSS em uma única folha de estilo no `PainelCuradoria`.
  - Tornar `ProvedorImagemAresta.obter_pixmap_imediato` estritamente em memória RAM ($O(1)$, sem I/O de disco nem `QImage.loadFromData` na thread de UI) e substituir a criação de uma `QThread` por card por um pool de **4 worker threads** (`MAX_WORKERS_THUMBNAIL = 4`, via `ThreadPoolExecutor`) em `ProvedorImagemAresta`, decodificando `QImage` em background e convertendo para `QPixmap` na thread de UI via sinal Qt.
  - Importar `ExtratorBlog` (`ddgs` / `bs4`) sob demanda apenas dentro de `criar_extratores_padrao()` em `dialogo_coletar_betas.py`.
  - Endereçamento $O(1)$ por caminho string (`curadoria_betas.conteudo.escaladas.<idx>`) em `CroquiController` e atalho direto para campos raiz de `Croqui` em `navegar_para_alvo` (`editor/commands/comandos_protobuf.py`).
  - Adiar o recálculo de `WidgetPainelQualidade` quando o widget não estiver visível (`not self.isVisible()`, atualizando no `showEvent`) e ignorar mutações `repeated_*` de `CuradoriaBetasEscalada` em `WidgetEditorDados`.
  - Adicionar testes de benchmark automatizados garantindo que a primeira abertura/hidratação em fatias e o clique individual de aprovar/rejeitar executem em `< 8 ms` por frame.
- **Promoção de "Vídeos de beta e curadoria em dia" para a Etapa 2 (`100 pontos`) e Leitura de `curadoria_betas`**:
  - Mover a tarefa de vídeos de beta e curadoria da Etapa 3 (`10 pts`) para a **Etapa 2 (`100 pts`, `id_tarefa="etapa2_videos_betas"`)** em `editor/core/avaliador_nota_qualidade.py`.
  - Detectar betas pendentes diretamente em `curadoria_betas` (`betas_nao_scorados` e `betas_nao_revisados` em `curadoria_betas.yaml` / `croqui.curadoria_betas.conteudo.escaladas`), sincronizado com o aviso de compilação do `validador_croqui.py`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `curation-panel`: Reconciliação incremental de cards sem recriação total da lista, eliminação de relayout patológico e orçamento estrito `< 8 ms` por clique individual de aprovação/rejeição.
- `painel-nota-qualidade-croqui`: Promoção do critério "Vídeos de beta e curadoria em dia" para a Etapa 2 (`100 pontos`) e verificação de pendências via `curadoria_betas` (`betas_nao_scorados` e `betas_nao_revisados`).

## Impact

- `coleta_de_betas/curadoria/painel_curadoria.py` e `coleta_de_betas/curadoria/painel_curadoria_test.py`
- `coleta_de_betas/curadoria/provedor_imagem_aresta.py` e `coleta_de_betas/curadoria/provedor_imagem_aresta_test.py`
- `editor/commands/comandos_protobuf.py` e `editor/controllers/croqui_controller.py`
- `editor/views/widget_painel_qualidade.py`, `editor/views/widget_painel_qualidade_test.py` e `editor/views/widget_editor_dados.py`
- `editor/core/avaliador_nota_qualidade.py` e `editor/core/avaliador_nota_qualidade_test.py`
