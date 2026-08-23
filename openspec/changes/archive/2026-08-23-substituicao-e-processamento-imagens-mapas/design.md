## Context

O editor gráfico do Aresta possui áreas dedicadas para edição de mapas de setores/grupos ([`WidgetEditorMapas`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/widget_editor_mapas.py)) e edição de imagens ([`WidgetEditorImagens`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/legacy_views/widget_editor_imagens.py)). Atualmente:
1. O diálogo de adicionar novo mapa ([`DialogoAdicionarMapa`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/dialogos/dialogo_adicionar_mapa.py)) é rudimentar: apresenta uma área vazia sem botão explícito de seleção, não exibe metadados ricos (dimensões, tamanho em KB/MB, formato original), não faz pré-processamento WebP consistente e só avisa sobre nomes duplicados ao clicar em OK.
2. Não há opção no Editor de Mapas para substituir a imagem de um mapa existente ou abri-la diretamente na aba do Editor de Imagens.
3. No Editor de Imagens, não há botão/fluxo dedicado para substituir um arquivo de imagem existente por uma nova foto/arquivo.
4. Para garantir a segurança dos dados e o funcionamento perfeito de Desfazer/Refazer (Undo/Redo), **todas as mutações em imagens e mapas devem ocorrer estritamente em memória RAM (Shadow State no `CroquiModel`)** com comandos `QUndoCommand`. Apenas o salvamento final persiste os arquivos fisicamente para o disco.
5. Se uma imagem for alterada em uma visão (Editor de Dados, Editor de Mapas ou Editor de Imagens), **todas as outras visões devem se sincronizar reativamente de forma automática**.

## Goals / Non-Goals

**Goals:**
- **Operação Estritamente em RAM (Shadow State) e QUndoCommand**:
  - Toda adição, substituição ou remoção de imagem em qualquer tela opera exclusivamente no buffer de memória `_imagens_em_memoria` do `CroquiModel`.
  - Mutações são encapsuladas em comandos `QUndoCommand` registrados na `QUndoStack` global.
  - A persistência no sistema de arquivos só ocorre quando o usuário aciona o salvamento do croqui.
- **Sincronização Reativa Universal**:
  - O `CroquiModel` emite o sinal `imagem_alterada(caminho_relativo)`.
  - `WidgetEditorMapas`, `WidgetEditorImagens` e `WidgetCampoImagem` assinam este sinal e recarregam automaticamente as imagens em cena e miniaturas caso a imagem alterada corresponda à que estão exibindo.
- **Diálogo de Adição de Mapas Robusto**:
  - Fornecer botão evidente "Selecionar Imagem..." em adição à área de arrastar e soltar (Drag & Drop).
  - Exibir painel de metadados ricos (largura $\times$ altura em pixels, tamanho do arquivo e formato).
  - Pré-processamento automático WebP em memória via [`processar_e_comprimir_imagem_para_webp`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/processamento_imagem_campo.py).
  - Campo de nome de arquivo com sanitização de slug em tempo real e indicador visual de conflito com arquivos já existentes na RAM ou no disco.
- **Substituição de Imagem no Editor de Mapas**:
  - Adicionar botão "Substituir Imagem..." no [`WidgetEditorMapas`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/widget_editor_mapas.py) que permite escolher um novo arquivo, aplica compressão WebP em RAM via comando `QUndoCommand` e recarrega a cena preservando os POIs e geometrias.
- **Navegação do Mapa para o Editor de Imagens**:
  - Adicionar botão "Abrir no Editor de Imagens" no [`WidgetEditorMapas`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/widget_editor_mapas.py) que dispara a alternância de aba e seleção na [`PaginaImagens`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/legacy_views/area_principal.py).
- **Substituição de Imagem no Editor de Imagens**:
  - Adicionar botão "Substituir Imagem..." no [`WidgetEditorImagens`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/legacy_views/widget_editor_imagens.py) aplicando compressão WebP em RAM e suporte integral a Undo/Redo no histórico global.
- **Qualidade & TDD**:
  - 100% de cobertura de código em testes unitários e testes de integração de ponta a ponta.

**Non-Goals:**
- Não alterar o formato de serialização dos mapas em arquivos Markdown (`ArquivoMarkdown`).
- Não alterar as coordenadas relativas normalizadas dos POIs já gravados nos mapas.

## Decisions

### Decisão 1: Shadow State em RAM e Persistência Tardia
- O `CroquiModel` gerencia todas as imagens através de `_imagens_em_memoria: dict[str, bytes]`.
- `CroquiModel.obter_bytes_imagem(caminho_relativo)` busca primeiro no buffer de RAM e só lê do disco caso não exista na memória.
- Nenhuma operação de interface escreve diretamente no disco durante a edição. Toda escrita física ocorre em `CroquiModel.extrair_arquivos_e_serializar`.

### Decisão 2: Mutações 100% via `QUndoCommand`
- Todas as substituições de imagens, adições de mapas e remoções são executadas através de comandos:
  - `CmdSubstituirImagemMemoria`: armazena `caminho_relativo`, `bytes_antigos` e `bytes_novos`. No `redo()`, atualiza a RAM e emite `imagem_alterada`. No `undo()`, restaura os `bytes_antigos` e emite `imagem_alterada`.
  - `CmdAdicionarMapaMemoria`: adiciona o mapa e a imagem pré-processada em RAM. No `undo()`, desfaz a inclusão.
  - `CmdRemoverMapaMemoria`: remove o mapa e a imagem da RAM, preservando cópia para o `undo()`.

### Decisão 3: Sincronização Reativa Global via Sinal `imagem_alterada`
- O `CroquiModel` emite `imagem_alterada = pyqtSignal(str)`.
- Todos os widgets de imagem (`WidgetEditorMapas`, `WidgetEditorImagens`, `WidgetCampoImagem`) assinam este sinal. Se a imagem visualizada for a alterada, o widget recarrega seus bytes da memória instantaneamente, garantindo sincronização imediata em toda a aplicação.

### Decisão 4: Centralização do Pré-processamento na Biblioteca Pura
- Reutilizar as funções puras de [`editor/core/processamento_imagem_campo.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/processamento_imagem_campo.py) para leitura de metadados (`obter_metadados_imagem_de_bytes`), sanitização (`sanitizar_nome_imagem`) e conversão/compressão WebP (`processar_e_comprimir_imagem_para_webp`).

### Decisão 5: Diálogo Moderno de Imagem com Feedback Visual Imediato
- O [`DialogoAdicionarMapa`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/dialogos/dialogo_adicionar_mapa.py) conta com:
  1. Cabeçalho com botão visível `QPushButton("Selecionar Imagem...")` e suporte a drag & drop.
  2. Área de pré-visualização central com imagem ajustada e rótulo de metadados: `${W}x${H} px | ${Tamanho formatado} | ${Formato}`.
  3. Campo de texto para o nome do arquivo com sanitização contínua e rótulo de validação dinâmico (alerta em vermelho se já existir na RAM/disco e bloqueio do botão OK).
  4. Pré-processamento WebP imediato em memória.

## Risks / Trade-offs

- **[Risco] Alto consumo de memória com imagens volumosas não salvas**:
  - *Mitigação*: Como todas as imagens passam pelo pré-processamento e compressão WebP antes de irem para a RAM, cada imagem ocupa tipicamente menos de 300KB a 1MB em memória.
- **[Risco] Sobrescrita acidental de arquivos na pasta `imagens/`**:
  - *Mitigação*: O diálogo valida dinamicamente contra os arquivos do disco e o buffer de memória, impedindo nomes duplicados involuntários.
