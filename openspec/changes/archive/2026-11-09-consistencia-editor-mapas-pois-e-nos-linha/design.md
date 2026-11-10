# Design

## Context

Consulte `proposal.md` para a motivação completa. Atualmente:
1. `Mapa.PontoDeInteresse` (`aresta_api/proto/croqui.proto`) possui `uid = 13`, `rotulo = 12`, `texto_visivel = 11`, `tamanho_fonte = 14`, `cor = 10`, mas não possui um campo booleano para preenchimento opaco (`preenchido`). Em `BaseItemPOI.atualizar_estilo_visual`, o preenchimento é fixo em `alpha = 60` e o texto em `QColor(0, 0, 0)`, enquanto `BaseItemPOI.hoverLeaveEvent` e `WidgetEditorMapas.remover_destaque_pois` sobrescrevem o estilo com verde fixo `QColor(0, 255, 0, 50)`.
2. `DialogoEdicaoPOI` bloqueia o botão `OK` se `input_id` estiver vazio e apresenta nomes ambíguos (`"ID (Referência)"`, `"Label (Texto)"`, `"Texto Visível"`) sem explicação contextual.
3. `AlcaNoTrajeto` (`editor/views/widget_editor_mapas.py`) suporta `no.raio` apenas para os tipos `1` (`CIRCULO_IDENTIFICADOR`), `2` (`INICIO_AGACHADO`) e `11` (`FIM_TOP`), não aceita `Ctrl + arrastar` para redimensionar e não possui slider de redimensionamento em lote (*bulk*) na barra lateral nem reescalonamento de `no.raio` / `linha.espessura` em `redimensionar_pois_proporcionalmente`.
4. A criação de `circulo` e `retangulo` ocorre apenas no centro da viewport sem vínculo automático com a referência selecionada, sem memória do último estilo usado e sem opção de duplicar elementos ou criar diretamente via clique direito no fundo do mapa.

## Goals / Non-Goals

**Goals:**
- Adicionar `bool preenchido = 15` em `Mapa.PontoDeInteresse` e suportar renderização 100% opaca com contraste automático de texto e preservação fiel de cor/preenchimento após hover e highlight de referências.
- Tornar `DialogoEdicaoPOI` autoexplicativo com ícones `ⓘ` (tooltips) para `ID (UID)`, `Rótulo (Codenome)` e `Texto Visível`, permitindo criar POIs sem rótulo e sem texto visível (gerando `uid` automaticamente).
- Unificar a experiência de redimensionamento entre POIs avulsos e nós/linhas de rota: `Ctrl + arrastar` em `AlcaNoTrajeto`, escala por `no.raio` para todos os tipos de nó, sliders bulk para `Nós de Linha` e `Espessura Linhas`, e reajuste proporcional de `no.raio` e `linha.espessura` em `geometrias_poi.py`.
- Agilizar a criação e vinculação de POIs com menu de contexto no ponto clicado do mapa, auto-vinculação à referência selecionada, memória de estilo na sessão e duplicação de POI.

**Non-Goals:**
- Alterar o formato de serialização de referências (`Mapa.Referencia`) ou o algoritmo de curvas Catmull-Rom.
- Introduzir gradientes ou níveis arbitrários de transparência (`0..255`) além do modo translúcido padrão (`alpha=60`) e sólido/opaco (`preenchido=True`, `alpha=255`).

## Decisions

### 1. Campo `bool preenchido = 15` e Contraste Automático Pura em `geometrias_poi.py`
- **Decisão**:
  - Adicionar `bool preenchido = 15;` em `Mapa.PontoDeInteresse` (`aresta_api/proto/croqui.proto`).
  - Criar em `editor/core/geometrias_poi.py` a função pura `calcular_cor_texto_contraste(cor_hex: str, preenchido: bool) -> str`:
    - Quando `preenchido` for `False`, retorna `"#000000"` (mantendo o texto preto sobre fundo translúcido).
    - Quando `preenchido` for `True`, calcula a luminância relativa $L = 0.299 R + 0.587 G + 0.114 B$ da cor ativa; se $L < 140$, retorna `"#FFFFFF"` (branco), caso contrário `"#000000"` (preto).
  - Em `BaseItemPOI.atualizar_estilo_visual()`:
    - Ler `preenchido = bool(self.pt_dict.get("preenchido", False))`.
    - Se `preenchido` for `True`, usar `alpha = 255` no `QBrush` da cor ativa; caso contrário, manter `alpha = 60`.
  - Em `BaseItemPOI.hoverLeaveEvent` e `WidgetEditorMapas.remover_destaque_pois`:
    - Substituir o reset verde hardcoded por `gui_item.atualizar_estilo_visual()`.
    - Durante `destacar_pois_temporariamente`, usar `QColor(0, 255, 255, 220 if preenchido else 150)` e `QPen(QColor(0, 255, 255), 3)` para que bolinhas opacas sem texto fiquem imediatamente visíveis em Ciano quando sua referência for selecionada ou receber hover.
- **Alternativas consideradas**:
  - Usar um `int32 opacidade` livre de `0` a `100`: descartado por adicionar complexidade desnecessária na UI quando os dois casos reais de uso em croquis são caixa translúcida sobre texto de fundo vs. marcador/caixa sólida opaca.

### 2. `DialogoEdicaoPOI`: Ícones `ⓘ` Explicativos e Permissão de POIs Sem Rótulo/Texto
- **Decisão**:
  - Se `id_atual` passado ao `DialogoEdicaoPOI` estiver vazio (criação de novo POI), pré-preencher `self.input_id` com um `gerar_uid()` válido (ou gerar no `accept()`/`obter_valores()` caso o usuário limpe o campo), mantendo o botão `OK` sempre habilitado.
  - Adicionar ao lado de cada rótulo de campo no `QFormLayout` do `DialogoEdicaoPOI` um badge informativo estilizado `ⓘ` (`QLabel` com `setToolTip` rico e cursor `WhatsThisCursor`):
    - **`ID (UID) ⓘ`**: *"Identificador único interno (UUID) usado para vincular este elemento às referências. Gerado automaticamente."*
    - **`Rótulo (Codenome) ⓘ`**: *"Identificador lógico exibido na lista de vias/setores do app (ex: '132'). NÃO é desenhado sobre a imagem do mapa. Deixe vazio para marcadores auxiliares (como bolinhas sem texto)."*
    - **`Texto Visível ⓘ`**: *"Texto desenhado visualmente dentro da forma por cima da imagem do mapa (use quando a arte do mapa não possui o número impresso)."*
  - Adicionar `QCheckBox("Preenchimento Sólido (Opaco)")` (`self.chk_preenchido`) ao `DialogoEdicaoPOI`.

### 3. Paridade de Redimensionamento em `AlcaNoTrajeto` e Sliders Bulk de Linhas
- **Decisão**:
  - **`Ctrl + Arrastar` em `AlcaNoTrajeto`**:
    - Em `AlcaNoTrajeto.mousePressEvent`, quando `event.modifiers() == Qt.KeyboardModifier.ControlModifier`, iniciar modo `self.redimensionando_no = True`, guardando `self.raio_inicio = self.obter_raio()` e a posição inicial da cena.
    - Em `mouseMoveEvent`, quando `self.redimensionando_no` for `True`, calcular o novo raio pela distância radial ao centro do nó (`max(3, int(round(hypot(dx, dy))))`), atualizar `self.item_linha.pt_dict["linha"]["conteudo"]["nos"][self.index_no]["raio"] = novo_raio`, chamar `self.atualizar_estilo()` e `self.update()`.
    - Em `mouseReleaseEvent`, finalizar `self.redimensionando_no = False` e registrar a mutação via `registrar_movimento_final(self.item_linha, self.estado_inicial_linha)`.
  - **Escala por `no.raio` para todos os tipos de nó**:
    - Em `AlcaNoTrajeto.obter_raio()`, definir o raio base padrão conforme o tipo quando `no.raio <= 0`: `14` para tipos `1, 2, 11`, `10` para `PARADA_INTERMEDIARIA (4)` / `TOP_PARADA (5)`, e `8` para os demais (`PROTECAO_FIXA (3)`, `CRUX (6)`, `SETA_DIRECIONAL (7)`, `PROTECAO_MOVEL (8)`, `PROTECAO_PITON (9)`, `PROTECAO_FITA (10)`, `BURACO_CLIFF (12)`).
    - Em `atualizar_estilo()` e `paint()`, substituir as constantes hardcoded (`8`, `12`) por proporções de `r = self.obter_raio()`, permitindo que qualquer marcador seja aumentado ou diminuído via `Ctrl + arrastar`, menu de contexto (`"Tamanho do Marcador (Raio: Xpx)..."`) ou slider bulk.
  - **Sliders Bulk para `Nós de Linha` e `Espessura Linhas`**:
    - Adicionar dois novos sliders (`-50%` a `+50%`) na barra lateral esquerda (`slider_nos_linha` e `slider_espessura_linha`), integrados a `ao_pressionar_slider_bulk`, `ao_mover_slider_bulk` e `ao_soltar_slider_bulk` com suporte a `CmdMacro`.
  - **Reajuste Proporcional em `geometrias_poi.py`**:
    - Em `redimensionar_pois_proporcionalmente`, quando `poi.HasField("linha")`, escalar `linha.espessura` (se `> 0`) e, para cada nó em `linha.conteudo.nos` e `linha.compilado.marcadores`, escalar `no.raio` (se `> 0`) e `no.tamanho_fonte` (se `> 0`) por `escala_media = sqrt(s_x * s_y)`.

### 4. Menu de Contexto no Fundo do Mapa, Auto-Vinculação, Memória de Estilo e Duplicação
- **Decisão**:
  - **Memória de Estilo na Sessão**:
    - `WidgetEditorMapas` manterá `self._ultimo_estilo_poi` com `raio_circulo`, `largura_retangulo`, `altura_retangulo`, `cor`, `preenchido` e `tamanho_fonte`, atualizado sempre que o usuário criar ou editar um POI.
  - **Menu de Contexto no Fundo do Mapa**:
    - No `VisualizadorMapa`, ao clicar com o botão direito em uma área sem item gráfico interativo (e fora dos modos de desenho/rota/conversão), exibir um `QMenu` com:
      - `"Adicionar Círculo Aqui..."` (abre `DialogoEdicaoPOI` e posiciona na coordenada clicada)
      - `"Adicionar Ponto Opaco Aqui"` (cria imediatamente na coordenada clicada um círculo com `preenchido=True`, sem texto/rótulo, usando `cor` e `raio` recentes — padrão `#000000` e `raio=10` — sem precisar abrir modal!)
      - `"Adicionar Retângulo Aqui..."` (abre `DialogoEdicaoPOI` e posiciona na coordenada clicada)
      - `"Iniciar Nova Rota Aqui..."` (abre `DialogoNovaRotaMapa` e já inicia o primeiro nó na coordenada clicada)
  - **Auto-Vinculação à Referência Ativa**:
    - Criar método auxiliar `_vincular_poi_a_referencia_ativa_se_houver(uid_poi: str)` em `WidgetEditorMapas`: se houver `referencia_linkagem_ativa` ou `referencia_selecionada` no mapa atual, agrupa `adicionar_poi` + `alterar_referencia` (adicionando `uid_poi` a `pontos_uids`) em um único `CmdMacro` no `mapas_controller`.
  - **Duplicar Elemento**:
    - Adicionar ação `"Duplicar Elemento"` no menu de contexto de `BaseItemPOI`, criando uma cópia do POI deslocada em `(+20, +20)` com novo `uid` via `mapas_controller.adicionar_poi` (e vinculando ou mantendo desvinculado de forma limpa).

## Risks / Trade-offs

- **[Risco] Contraste de texto em cores intermediárias quando `preenchido=True`** → Mitigação: Usar fórmula padrão de luminância perceptiva ITU-R BT.601 ($0.299R + 0.587G + 0.114B$) com limiar em `140`, garantindo texto branco para cores escuras/médias (preto, azul, roxo, vermelho) e texto preto para cores claras (amarelo, verde-lima, ciano, branco).
- **[Risco] Conflito do clique direito no fundo do mapa com cancelamento de modos interativos** → Mitigação: Só exibir o menu de contexto do fundo do mapa quando nenhum modo interativo (`modo_desenho`, `modo_nova_rota`, `modo_conversao`, `modo_linkagem`, `modo_camera`) estiver ativo e quando não houver item POI/alça sob o cursor.
