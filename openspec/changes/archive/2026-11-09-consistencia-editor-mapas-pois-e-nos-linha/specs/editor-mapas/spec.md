# Spec Delta

## MODIFIED Requirements

### Requirement: Seletor de Cores de Alto Contraste para Elementos do Mapa
O sistema SHALL fornecer um seletor visual de cores no diálogo de edição e no menu de contexto dos elementos do mapa (linhas, círculos, retângulos, quadrados e polígonos), disponibilizando a paleta recomendada de alto contraste para rocha (Vermelho, Laranja, Amarelo, Verde Lima, Ciano, Roxo, Branco, Cinza), opção de cor personalizada e opção de restauração para a cor padrão do sistema, com suporte a `QUndoCommand`. O sistema SHALL preservar a cor customizada e o estado de preenchimento (`preenchido`) do elemento após eventos de passagem de mouse (`hoverLeaveEvent`) e após a remoção de destaques temporários de referências (`remover_destaque_pois`).

#### Scenario: Alteração de Cor de Traçado
- **WHEN** o usuário seleciona uma nova cor na paleta para uma linha existente
- **THEN** o sistema SHALL atualizar a cor da linha e de seus marcadores na cena imediatamente e registrar o comando de alteração de cor na pilha de histórico.

#### Scenario: Alteração de Cor de Formas Geométricas via Menu de Contexto
- **WHEN** o usuário clica com botão direito sobre um círculo, retângulo, quadrado ou polígono e seleciona uma cor da paleta ou uma cor personalizada
- **THEN** o sistema SHALL atualizar visualmente a borda e o preenchimento da forma geométrica na cena imediatamente, além das alças de vértices no caso de polígonos, e registrar a alteração no histórico de comandos (`QUndoStack`).

#### Scenario: Restauração da Cor Padrão do Sistema
- **WHEN** o usuário seleciona a opção "Padrão do Sistema" no submenu de cores de uma forma geométrica
- **THEN** o sistema SHALL remover a cor customizada do elemento, restaurar as cores originais da geometria (verde para círculos/retângulos e azul para polígonos, respeitando `preenchido`) e registrar a alteração no histórico de comandos.

#### Scenario: Preservação de Cor Customizada após Hover e Destaque de Referência
- **WHEN** um Ponto de Interesse possui cor customizada (ex: `#000000` ou `#808080`) e o cursor do mouse sai do elemento ou de um card de referência na barra lateral
- **THEN** o sistema SHALL restaurar a cor customizada e o estilo de preenchimento configurados no POI em vez de sobrescrevê-lo com verde padrão.

#### Scenario: Desfazer e Refazer Alteração de Cor
- **WHEN** o usuário executa desfazer (Undo) ou refazer (Redo) após alterar a cor de uma forma geométrica
- **THEN** o sistema SHALL atualizar a renderização do elemento na cena imediatamente para refletir a cor correspondente ao estado restaurado.

### Requirement: Reajuste Proporcional Puro de Geometrias de POIs
O sistema SHALL fornecer na biblioteca pura `editor/core/geometrias_poi.py` a função `redimensionar_pois_proporcionalmente` capaz de reescalar as coordenadas, dimensões, espessuras de linha (`linha.espessura`), raios de nós (`no.raio`) e tamanhos de fonte (`tamanho_fonte`) de todas as geometrias de `PontoDeInteresse` (`circulo`, `quadrado`, `retangulo`, `poligono` e `linha.conteudo.nos`) de $(W_{\text{antigo}}, H_{\text{antigo}})$ para $(W_{\text{novo}}, H_{\text{novo}})$.

#### Scenario: Reajuste proporcional de círculos, quadrados, retângulos, polígonos e linhas
- **WHEN** `redimensionar_pois_proporcionalmente` é invocada com uma lista de POIs e fatores de escala $s_x = W_{\text{novo}} / W_{\text{antigo}}$ e $s_y = H_{\text{novo}} / H_{\text{antigo}}$
- **THEN** a função SHALL retornar novas mensagens `PontoDeInteresse` com coordenadas `x` e `comprimento` multiplicados por $s_x$, coordenadas `y` e `largura` multiplicadas por $s_y$, `raio`, `lado`, `linha.espessura` (quando $> 0$), `no.raio` (quando $> 0$) e `tamanho_fonte` (quando $> 0$, tanto no POI quanto nos nós de linha) multiplicados pela média geométrica $\sqrt{s_x \cdot s_y}$ (com mínimo $1$), e todos os vértices de `poligono` e nós de `linha.conteudo.nos` reescalados por $(s_x, s_y)$

## ADDED Requirements

### Requirement: Preenchimento Sólido Opaco e Contraste Automático em Pontos de Interesse
O sistema SHALL suportar o campo booleano opcional `preenchido` em `Mapa.PontoDeInteresse` para renderizar formas geométricas (`circulo`, `retangulo`, `quadrado` e `poligono`) com fundo 100% opaco na cor ativa do elemento e ajustar automaticamente a cor de `texto_visivel` para alto contraste (branco em fundo escuro, preto em fundo claro). O usuário SHALL poder alternar `preenchido` pelo diálogo de edição e pelo menu de contexto com suporte a Undo/Redo, mantendo o destaque Ciano ao selecionar a referência.

#### Scenario: Criação e alternância de círculo opaco sem texto vinculado a referência
- **WHEN** o usuário cria um círculo sem texto com `preenchido = true` e cor `#000000` (ou alterna `"Alternar Preenchimento (Opaco / Translúcido)"` no menu de contexto) e o vincula a uma `Referencia`
- **THEN** o círculo SHALL ser renderizado com preenchimento preto 100% opaco no estado normal e SHALL receber destaque Ciano vibrante quando a referência vinculada for selecionada ou receber hover, permitindo desfazer e refazer a alteração de preenchimento.

#### Scenario: Contraste automático de texto visível em forma preenchida
- **WHEN** um Ponto de Interesse possui `preenchido = true` e `texto_visivel` preenchido
- **THEN** o sistema SHALL renderizar o texto em branco (`#FFFFFF`) quando a luminância da cor de fundo for escura e em preto (`#000000`) quando a cor de fundo for clara.

### Requirement: Criação de POIs Sem Rótulo e Explicação Contextual no Diálogo de Edição
O diálogo de edição de Ponto de Interesse SHALL permitir confirmar a criação ou edição de um elemento mesmo quando `rotulo` e `texto_visivel` estiverem vazios, gerando `uid` automaticamente quando omitido. O diálogo SHALL exibir ícones informativos (`ⓘ`) com tooltips explicando a diferença entre o ID interno (`uid`), o Rótulo lógico da referência (`rotulo`, exibido na lista do aplicativo) e o Texto Visível (`texto_visivel`, desenhado sobre a imagem do mapa).

#### Scenario: Confirmação de POI mudo (sem rótulo e sem texto visível)
- **WHEN** o usuário abre o diálogo de edição para criar um novo POI, deixa `rotulo` e `texto_visivel` vazios e clica em OK
- **THEN** o botão OK SHALL estar habilitado e o sistema SHALL criar o POI com um `uid` UUIDv4 válido e `rotulo` vazio, sem poluir o codenome extraído da referência à qual venha a ser vinculado.

#### Scenario: Exibição de tooltips explicativos nos ícones de informação do diálogo
- **WHEN** o usuário inspeciona os ícones `ⓘ` ao lado dos campos `ID (UID)`, `Rótulo (Codenome)` e `Texto Visível` no diálogo de edição de POI
- **THEN** cada ícone SHALL apresentar um tooltip claro explicando sua finalidade e a diferença entre o identificador lógico da referência (`rotulo`) e o texto desenhado sobre a arte do mapa (`texto_visivel`).

### Requirement: Redimensionamento Interativo e em Lote de Nós e Espessura de Linhas
O sistema SHALL permitir redimensionar interativamente qualquer nó de linha (`AlcaNoTrajeto`) via `Ctrl + arrastar` no mapa, escalando proporcionalmente o desenho de todos os tipos semânticos de nó pelo campo `raio` (e a fonte quando `tamanho_fonte` for `0`) com registro no histórico. O painel lateral SHALL fornecer sliders de redimensionamento em lote (`-50%` a `+50%`) para `Nós de Linha` e `Espessura de Linhas`, além de atualizar posição e fonte em tempo real nos sliders de `Retângulos` e `Quadrados`.

#### Scenario: Redimensionamento de nó de linha com Ctrl + arrastar
- **WHEN** o usuário segura `Ctrl`, clica e arrasta sobre qualquer nó de uma linha (`CIRCULO_IDENTIFICADOR`, `PROTECAO_FIXA`, `PARADA_INTERMEDIARIA`, `TOP_PARADA`, `CRUX`, `PROTECAO_MOVEL`, `SETA_DIRECIONAL`, etc.)
- **THEN** o sistema SHALL redimensionar o raio visual do nó (e o tamanho da fonte quando automático) em tempo real durante o arraste e registrar um único comando reversível no `QUndoStack` ao soltar o mouse.

#### Scenario: Redimensionamento em lote de Nós de Linha e Espessura de Linhas via sliders
- **WHEN** o usuário move e solta o slider bulk de `Nós de Linha` ou `Espessura Linhas` no painel lateral
- **THEN** o sistema SHALL escalar em tempo real os raios de todos os nós de linha ou a espessura de todas as linhas do mapa ativo, registrar as alterações agrupadas em `CmdMacro` no histórico e retornar o slider para `0%`.

#### Scenario: Atualização de texto e reset do slider bulk de Quadrados e Retângulos
- **WHEN** o usuário move e solta os sliders bulk de `Retângulos` ou `Quadrados`
- **THEN** o sistema SHALL atualizar em tempo real a posição e o tamanho da fonte automática dos textos visíveis durante o arraste e resetar ambos os sliders e rótulos percentuais para `0%` ao soltar.

### Requirement: Criação Posicionada no Clique, Auto-Vinculação, Memória de Estilo e Duplicação
O Editor de Mapas SHALL fornecer menu de contexto no fundo do mapa para adicionar Círculo, Ponto Opaco, Retângulo ou Nova Rota diretamente na coordenada clicada, auto-vinculando o novo POI à referência selecionada (ou ativa em vinculação) no painel lateral. O editor SHALL memorizar na sessão o último estilo e dimensões usados ao criar novos POIs e fornecer a ação "Duplicar Elemento" no menu de contexto de POIs existentes com Undo/Redo.

#### Scenario: Adição de Ponto Opaco ou Círculo no ponto clicado com auto-vinculação à referência selecionada
- **WHEN** uma referência está selecionada no `PainelReferencias` e o usuário clica com o botão direito em um ponto vazio do mapa e aciona `"Adicionar Ponto Opaco Aqui"` (ou `"Adicionar Círculo Aqui..."`)
- **THEN** o sistema SHALL criar o novo POI centrado exatamente na coordenada da cena onde ocorreu o clique e adicioná-lo automaticamente a `pontos_uids` da referência selecionada em uma operação reversível no histórico.

#### Scenario: Duplicação de POI existente mantendo estilo e dimensões
- **WHEN** o usuário clica com o botão direito sobre um POI existente (`circulo`, `retangulo` ou `quadrado`) e seleciona `"Duplicar Elemento"`
- **THEN** o sistema SHALL criar um novo POI com `uid` único deslocado ligeiramente do original, copiando sua geometria, dimensões, `cor`, `preenchido` e `tamanho_fonte`, registrando a adição no histórico.
