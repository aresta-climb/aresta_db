# Tasks

## 1. Cache de `QPixmap` em RAM e Endereçamento $O(1)$ (`ProvedorImagemAresta`, `comandos_protobuf`, `CroquiController`)

- [x] 1.1 Em `coleta_de_betas/curadoria/provedor_imagem_aresta.py` e `coleta_de_betas/curadoria/provedor_imagem_aresta_test.py`, adicionar cache de `QPixmap` já escalado (`_cache_pixmap_ram`) para retornar `QPixmap` em $O(1)$ sem repetir `QImage.loadFromData`, verificando com `uv run pytest coleta_de_betas/curadoria/provedor_imagem_aresta_test.py -n 0 -v`.
- [x] 1.2 Em `editor/commands/comandos_protobuf.py`, `editor/controllers/croqui_controller.py` e `editor/controllers/croqui_controller_test.py`, otimizar `navegar_para_alvo` para campos raiz de `Croqui` ($O(1)$) e endereçar `curadoria_betas.conteudo.escaladas.<idx>` por string de caminho nas operações de curadoria, verificando com `uv run pytest editor/controllers/croqui_controller_test.py -n 0 -k "curadoria or score" -v`.

## 2. Reconciliação Incremental de Cards, Layout Leve e Benchmark `< 8 ms` (`PainelCuradoria`, `WidgetPainelQualidade`, `WidgetEditorDados`)

- [x] 2.1 Em `coleta_de_betas/curadoria/painel_curadoria.py` e `coleta_de_betas/curadoria/painel_curadoria_test.py`, implementar reconciliação incremental de cards em `atualizar_visualizacao()` (reutilizando cards existentes e atualizando seus callbacks sem destruir e recriar toda a lista), centralizar o CSS no `PainelCuradoria`, remover `wordWrap` patológico com `setFixedHeight` nos cards e adicionar teste de benchmark verificando média `< 8 ms` por clique individual de aprovação/rejeição com `uv run pytest coleta_de_betas/curadoria/painel_curadoria_test.py -n 0 -v`.
- [x] 2.2 Em `editor/views/widget_painel_qualidade.py`, `editor/views/widget_painel_qualidade_test.py` e `editor/views/widget_editor_dados.py`, adiar o recálculo de `WidgetPainelQualidade` quando a aba estiver oculta (`showEvent`) e ignorar sinais `repeated_*` de `CuradoriaBetasEscalada` em `WidgetEditorDados`, verificando com `uv run pytest editor/views/widget_painel_qualidade_test.py -n 0 -v`.

## 3. Tarefa "Vídeos de beta e curadoria em dia" na Etapa 2 (`100 pts`) (`avaliador_nota_qualidade`)

- [x] 3.1 Em `editor/core/avaliador_nota_qualidade.py` e `editor/core/avaliador_nota_qualidade_test.py`, promover a tarefa de vídeos de beta e curadoria para a Etapa 2 (`100` pontos, `etapa2_videos_betas`) e verificar pendências em `curadoria_betas` (`betas_nao_scorados` e `betas_nao_revisados`), verificando com `uv run pytest editor/core/avaliador_nota_qualidade_test.py editor/views/widget_painel_qualidade_test.py -n 0 -v` e `uv run ruff check`.

## 4. Pool de 4 Worker Threads de Thumbnail e Construção de Cards em Fatias na 1ª Abertura (`ProvedorImagemAresta`, `PainelCuradoria`, `dialogo_coletar_betas`)

- [x] 4.1 Em `coleta_de_betas/curadoria/provedor_imagem_aresta.py` e `coleta_de_betas/curadoria/provedor_imagem_aresta_test.py`, tornar `obter_pixmap_imediato` estritamente em memória RAM (zero leitura de disco na UI thread) e implementar o pool de 4 worker threads (`MAX_WORKERS_THUMBNAIL = 4`) via `solicitar_pixmap_assincrono`, `cancelar_callback_assincrono` e `encerrar_workers`, verificando com `uv run pytest coleta_de_betas/curadoria/provedor_imagem_aresta_test.py -n 0 -v`.
- [x] 4.2 Em `coleta_de_betas/curadoria/dialogo_coletar_betas.py`, `coleta_de_betas/curadoria/painel_curadoria.py` e `coleta_de_betas/curadoria/painel_curadoria_test.py`, mover a importação de `ExtratorBlog` para `criar_extratores_padrao()`, integrar os cards ao pool de 4 workers de `ProvedorImagemAresta` e implementar a hidratação progressiva de cards em fatias (`TAMANHO_FATIA_CARDS_PADRAO = 5`), verificando com `uv run pytest coleta_de_betas/curadoria/painel_curadoria_test.py coleta_de_betas/curadoria/dialogo_coletar_betas_test.py -n 0 -v`.
