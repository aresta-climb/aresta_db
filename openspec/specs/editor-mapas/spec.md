# editor-mapas Specification

## Purpose
Fornecer um editor visual para gerenciar Pontos de Interesse (POI) em mapas de setores e grupos de um croqui, permitindo a marcação precisa de áreas e a sincronização com o banco de dados YAML.
## Requirements
### Requirement: Editor de Pontos de Interesse (POI) em Mapas
O sistema SHALL fornecer um editor visual para gerenciar Pontos de Interesse (POI) e Referências em mapas de setores e grupos de um croqui, acessível primariamente integrado no painel principal em sua própria aba, respondendo a comandos da QUndoStack global e lendo diretamente do `CroquiModel`. A interface SHALL ser estruturada em três painéis horizontais (Mapas à esquerda, Visualizador ao centro, Referências à direita). O Visualizador ao centro SHALL suportar navegação através do arrasto da visualização (panning) quando o usuário clicar e arrastar no fundo da imagem (fora dos POIs). O editor visual SHALL suportar a renderização, criação e manipulação das geometrias `circulo`, `quadrado`, `retangulo` e `poligono`.
- **Filtragem Reativa da Lista de Mapas**: O sistema SHALL reconstruir a lista de mapas na barra lateral apenas em resposta a alterações estruturais ou mutações que afetem mensagens de mapas, ignorando eventos de alteração de campos puramente textuais (como descrições e conteúdos markdown).

#### Scenario: Acesso Embutido na Árvore de Dados
- **WHEN** o usuário seleciona um nó correspondente a um mapa na árvore do Editor de Dados e clica para abri-lo
- **THEN** o sistema SHALL carregar a aba de mapas na JanelaPrincipal, focando na visualização e edição do mapa e de seus Pontos de Interesse, com o estado sincronizado pelo `CroquiModel`.

#### Scenario: Visualização de mapas disponíveis
- **WHEN** o usuário abre a aba do editor de mapas
- **THEN** o sistema SHALL listar, na barra lateral, todos os mapas (`Mapa` protobuf messages) disponíveis na hierarquia do `CroquiModel` carregado.

#### Scenario: Arrasto da visualização pelo fundo do mapa
- **WHEN** o usuário clica em uma área do mapa (Visualizador) que não contém um POI e arrasta o cursor
- **THEN** o sistema SHALL mover a visualização do mapa (panning) correspondente ao movimento do mouse

#### Scenario: Manipulação de Quadrados e Polígonos
- **WHEN** o usuário visualiza ou interage com um mapa que possua os novos formatos de POI
- **THEN** o sistema SHALL renderizar adequadamente `quadrado` e `poligono` no visualizador

#### Scenario: Rejeição de Atualização da Lista por Alteração Textual
- **WHEN** um campo textual (`conteudo`, `descricao`, etc.) for alterado no modelo
- **THEN** o Editor de Mapas não deve reconstruir a lista lateral de mapas.


### Requirement: Substituição de Imagem no Editor de Mapas em Memória RAM
O sistema SHALL permitir a substituição da imagem de fundo de um mapa existente por uma nova imagem estritamente em memória RAM com suporte a `QUndoCommand`, aplicando pré-processamento e compressão automática para WebP e recarregando a cena visual enquanto preserva a lista e geometrias de Pontos de Interesse (POIs).

#### Scenario: Substituição de Imagem Bem-Sucedida com Undo/Redo
- **WHEN** o usuário aciona a ação "Substituir Imagem..." no Editor de Mapas e escolhe um novo arquivo de imagem
- **THEN** o sistema SHALL pré-processar a imagem para WebP, atualizar o buffer em memória RAM através de um comando `QUndoCommand` e recarregar a imagem de fundo na cena preservando os POIs, permitindo desfazer e refazer a operação.

### Requirement: Sincronização Reativa Global do Mapa
O sistema SHALL sincronizar automaticamente a cena e a imagem de fundo do mapa quando os bytes da imagem forem alterados em qualquer outra visão (Editor de Imagens ou Editor de Dados).

#### Scenario: Atualização Automática ao Alterar Imagem no Editor de Imagens
- **WHEN** a imagem do mapa atual for substituída ou modificada no Editor de Imagens
- **THEN** o Editor de Mapas SHALL detectar o sinal `imagem_alterada` e recarregar a nova imagem de fundo da memória RAM sem desalinhar os POIs existentes.

### Requirement: Acesso Direto do Mapa ao Editor de Imagens
O sistema SHALL fornecer uma ação na barra de ferramentas do Editor de Mapas para abrir e focar a imagem do mapa atualmente selecionado dentro do Editor de Imagens.

#### Scenario: Foco da Imagem no Editor de Imagens
- **WHEN** o usuário clica no botão "Abrir no Editor de Imagens" no Editor de Mapas
- **THEN** o sistema SHALL comutar a visualização para a aba de Imagens da Janela Principal e selecionar o arquivo de imagem do mapa atual.

### Requirement: Diálogo Robusto de Adição de Mapas
O sistema DEVE fornecer um diálogo robusto para adição de novos mapas contendo botão explícito de seleção de arquivos, suporte a arrastar e soltar (drag & drop), painel de metadados ricos (dimensões, tamanho formatado e formato), pré-processamento WebP automático em RAM e validação de nomes e colisões em tempo real.

#### Scenario: Seleção de Arquivo com Exibição de Metadados e Pré-processamento
- **WHEN** o usuário seleciona ou arrasta um arquivo de imagem no diálogo de adição de mapa
- **THEN** o sistema DEVE exibir a pré-visualização gráfica, apresentar resolução ($W \times H$), tamanho e formato original nos metadados, e pré-processar os bytes para WebP.

#### Scenario: Validação de Conflito de Nomes em Tempo Real
- **WHEN** o usuário digita um nome de arquivo que já existe no buffer de memória RAM (`_imagens_em_memoria`)
- **THEN** o sistema DEVE exibir alerta indicando conflito na memória RAM e desabilitar a confirmação
- **WHEN** o usuário digita um nome de arquivo que não existe na RAM mas já existe na pasta `imagens/` do disco
- **THEN** o sistema DEVE exibir alerta indicando conflito no disco e desabilitar a confirmação
- **WHEN** um mapa foi removido e sua imagem não está mais na memória RAM nem no disco
- **THEN** o sistema DEVE considerar o nome válido e liberar a confirmação

### Requirement: Ferramenta de Desenho e Edição de Traçados Vetoriais de Vias
O sistema SHALL fornecer uma ferramenta visual ("Nova Linha" / Caneta) no painel lateral do Editor de Mapas para permitir o desenho interativo de trajetos de vias e boulders diretamente sobre a imagem do mapa, calculando e exibindo a Spline Catmull-Rom em tempo real conforme os pontos são clicados.

#### Scenario: Início e Conclusão de Desenho de Linha
- **WHEN** o usuário clica no botão "Nova Linha", clica em múltiplos pontos da rocha na cena e confirma o término com duplo clique ou tecla Enter
- **THEN** o sistema SHALL criar um novo elemento visual do tipo `linha` com nós tipados (`CIRCULO_IDENTIFICADOR`, `PASSAGEM`, `TOP_PARADA`), calcular a curva suave na cena e registrar a adição no `CroquiModel` via `QUndoCommand`.

#### Scenario: Cancelamento do Desenho de Linha
- **WHEN** o usuário está no modo de desenho de linha e pressiona a tecla Esc ou botão direito sem nós suficientes
- **THEN** o sistema SHALL cancelar a operação, remover a linha temporária da cena e restaurar o cursor padrão de navegação.

### Requirement: Seletor de Cores de Alto Contraste para Elementos do Mapa
O sistema SHALL fornecer um seletor visual de cores no diálogo de edição e no menu de contexto dos elementos do mapa (linhas, círculos, retângulos, quadrados e polígonos), disponibilizando a paleta recomendada de alto contraste para rocha (Vermelho, Laranja, Amarelo, Verde Lima, Ciano, Roxo, Branco, Cinza), opção de cor personalizada e opção de restauração para a cor padrão do sistema, com suporte a `QUndoCommand`.

#### Scenario: Alteração de Cor de Traçado
- **WHEN** o usuário seleciona uma nova cor na paleta para uma linha existente
- **THEN** o sistema SHALL atualizar a cor da linha e de seus marcadores na cena imediatamente e registrar o comando de alteração de cor na pilha de histórico.

#### Scenario: Alteração de Cor de Formas Geométricas via Menu de Contexto
- **WHEN** o usuário clica com botão direito sobre um círculo, retângulo, quadrado ou polígono e seleciona uma cor da paleta ou uma cor personalizada
- **THEN** o sistema SHALL atualizar visualmente a borda e o preenchimento translúcido da forma geométrica na cena imediatamente, além das alças de vértices no caso de polígonos, e registrar a alteração no histórico de comandos (`QUndoStack`).

#### Scenario: Restauração da Cor Padrão do Sistema
- **WHEN** o usuário seleciona a opção "Padrão do Sistema" no submenu de cores de uma forma geométrica
- **THEN** o sistema SHALL remover a cor customizada do elemento, restaurar as cores originais da geometria (verde translúcido para círculos/retângulos e azul translúcido para polígonos) e registrar a alteração no histórico de comandos.

#### Scenario: Desfazer e Refazer Alteração de Cor
- **WHEN** o usuário executa desfazer (Undo) ou refazer (Redo) após alterar a cor de uma forma geométrica
- **THEN** o sistema SHALL atualizar a renderização do elemento na cena imediatamente para refletir a cor correspondente ao estado restaurado.

### Requirement: Manipulação e Alteração de Tipos de Nós com Undo/Redo
O sistema SHALL permitir a seleção, movimentação interativa e alteração do tipo semântico de nós individuais em uma linha existente no Editor de Mapas, com atualização instantânea da curva na cena e registro estrito na pilha de histórico `QUndoStack`.

#### Scenario: Movimentação de Nó de Traçado com Recálculo em Tempo Real
- **WHEN** o usuário clica e arrasta uma alça de nó de uma linha existente na cena
- **THEN** o sistema SHALL recalcular a spline suave continuamente durante o arrasto e, ao soltar o botão do mouse, registrar o comando de movimentação de nó na pilha de histórico.

#### Scenario: Alteração de Tipo de Nó via Menu de Contexto
- **WHEN** o usuário clica com botão direito sobre um nó da linha e seleciona um tipo semântico (ex: "Proteção Fixa", "Crux", "Parada / Top")
- **THEN** o sistema SHALL atualizar a renderização do nó para o ícone correspondente e registrar a modificação no modelo via comando de histórico.

#### Scenario: Inserção de Nó Intermediário
- **WHEN** o usuário clica com o botão direito sobre um segmento da linha e seleciona "Inserir Nó"
- **THEN** o sistema SHALL inserir um novo nó de `PASSAGEM` nas coordenadas clicadas, recalcular a spline e registrar a alteração no histórico.

### Requirement: Sincronização Estrutural Reativa e Validação de Mapa Ativo
O `WidgetEditorMapas` SHALL reagir imediatamente a alterações estruturais na lista de mapas do modelo (`CroquiModel`), incluindo adições e remoções de itens no campo `mapas`. Ao detectar remoção ou substituição de mapas, a interface SHALL reconstruir a lista lateral de mapas. Se o mapa atualmente exibido (`msg_mapa_proxy`) tiver sido removido ou não pertencer mais à árvore ativa do croqui, o `WidgetEditorMapas` SHALL descarregar a cena gráfica e o painel de referências, resetando a seleção. Além disso, antes de iniciar o desenho ou registrar novos elementos (POIs, linhas, nós, referências), o `WidgetEditorMapas` SHALL validar se o mapa atual ainda pertence à árvore ativa, bloqueando mutações órfãs.

#### Scenario: Remoção de mapa atualmente visualizado no editor
- **WHEN** um mapa selecionado no `WidgetEditorMapas` for removido da árvore do croqui por um comando do histórico
- **THEN** o `WidgetEditorMapas` SHALL detectar a remoção, atualizar a lista lateral de mapas, descarregar a cena gráfica e invalidar a referência ao mapa removido

#### Scenario: Tentativa de desenhar ou adicionar elementos em mapa não sincronizado
- **WHEN** o usuário tentar adicionar um POI, traçado ou referência sobre uma referência de mapa que não pertença à árvore ativa
- **THEN** o editor SHALL rejeitar a ação, emitir aviso visual e sincronizar a seleção com os mapas válidos existentes

#### Scenario: Restauração/Desfazer (Undo) da remoção de um mapa
- **WHEN** o usuário desfaz a remoção de um mapa no histórico
- **THEN** o `WidgetEditorMapas` SHALL atualizar a lista lateral incluindo o mapa restaurado e permitir sua seleção e edição normal

### Requirement: Desambiguação Seletiva de Topos Sob Demanda Topológica
O sistema SHALL aplicar desambiguação automática de nós finais de rotas de escalada no Editor de Mapas exclusivamente sob demanda topológica real. Círculos identificadores de final (`FIM_TOP`) com letras sequenciais (`A`, `B`, `C`...) SHALL ser gerados apenas quando duas ou mais rotas convergirem no mesmo ponto final ou quando duas ou mais rotas compartilharem trecho/início e se bifurcarem para finais distintos. Rotas isoladas sem nenhuma junção ou separação com outras rotas SHALL permanecer com o nó final configurado como nó de passagem (`PASSAGEM`) sem rótulo textual.

#### Scenario: Criação de múltiplas rotas isoladas no mesmo mapa
- **WHEN** o usuário cria duas ou mais rotas no mesmo mapa que não compartilham nós, linhas, inícios ou finais entre si
- **THEN** o sistema SHALL configurar o nó inicial de cada rota com seu respectivo número sequencial e SHALL manter o nó final de todas essas rotas isoladas como `PASSAGEM` com rótulo vazio, sem adicionar círculos ou letras de topo.

#### Scenario: Convergência de rotas no mesmo topo
- **WHEN** duas ou mais rotas com inícios distintos terminam exatamente no mesmo ponto final de topo (distância $\le 5.0\text{px}$)
- **THEN** o sistema SHALL atribuir a esse nó final compartilhado o tipo `FIM_TOP` com uma letra identificadora única (ex: "A") e atualizar as referências vinculadas.

#### Scenario: Bifurcação de rotas a partir de início ou tronco compartilhado
- **WHEN** duas ou mais rotas compartilham o início ou um segmento de linha e se dividem para pontos finais distintos (distância $> 5.0\text{px}$)
- **THEN** o sistema SHALL atribuir a cada um dos pontos finais distintos o tipo `FIM_TOP` com letras sequenciais distintas (ex: "A" e "B").

#### Scenario: Restauração de rota isolada após exclusão ou reversão de variante
- **WHEN** uma rota que possuía variante com identificadores de topo volta a ser a única rota do seu tronco após exclusão ou reversão (Undo) da variante
- **THEN** o sistema SHALL remover a letra identificadora do seu nó final e reverter o tipo do nó para `PASSAGEM` com rótulo vazio.

### Requirement: Unicidade Estrita de Identificadores de POI e Rótulo Inicial de Rotas
O sistema SHALL garantir identificadores de POI estritamente únicos para cada novo traçado ou elemento inserido no mapa ativo e no setor, impedindo colisões de chaves e referências duplicadas. Ao criar uma nova rota, o sistema SHALL calcular o próximo número de início sequencial disponível e gerar um ID de linha único considerando prioritariamente os POIs do mapa ativo e os mapas do setor desembrulhado, garantindo reversão completa e remoção de todos os itens gráficos da cena no histórico (Undo/Redo).

#### Scenario: Adição sequencial de múltiplas rotas avulsas ou conectadas no mapa ativo
- **WHEN** o usuário adiciona sucessivas rotas em um mapa
- **THEN** cada rota criada SHALL receber um ID de POI único (ex: `linha_1`, `linha_2`, `linha_3`), nós de início com números sequenciais distintos e não colidentes, e referências que apontem exclusivamente para os IDs de seus respectivos segmentos.

#### Scenario: Resolução de setor envelopado em ArquivoSetor ou proxy
- **WHEN** o setor fornecido estiver envelopado em mensagem `ArquivoSetor` (com conteúdo aninhado em `conteudo.mapas`) ou através de proxies de leitura
- **THEN** o sistema SHALL desembrulhar o setor corretamente para localizar todos os IDs e rótulos já existentes em todos os mapas do setor.

#### Scenario: Seleção independente de rotas no editor
- **WHEN** o usuário clica sobre o traçado de uma rota ou seleciona seu card de referência na barra lateral
- **THEN** apenas os segmentos pertencentes àquela rota específica SHALL ser destacados visualmente, sem selecionar ou destacar rotas vizinhas.

### Requirement: Preservação de POIs Não-Linha e Reversibilidade Atômica no Undo/Redo
O sistema SHALL garantir que operações de atualização de nós (como desambiguação de topos) localizem os índices reais e absolutos no array `pontos_de_interesse` do mapa ativo, preservando intactos todos os demais pontos de interesse existentes (como círculos de início ou retângulos) e permitindo que o histórico (`QUndoStack`) reverta a adição de forma limpa.

#### Scenario: Adição de nova rota em mapa contendo círculos ou outros POIs pré-existentes
- **WHEN** o usuário adiciona uma nova rota em um mapa que já contém círculos ou retângulos intercalados antes da nova linha
- **THEN** o sistema SHALL preservar intactos todos os círculos e retângulos existentes sem sobrescrever nenhum item por descompasso de índices.

#### Scenario: Desfazer atômico de rota sem deixar traçados órfãos na tela
- **WHEN** o usuário aciona Desfazer (Undo) após adicionar uma nova rota
- **THEN** todos os elementos visuais daquela rota SHALL ser imediatamente removidos da cena gráfica (`QGraphicsScene`), sem deixar traçados órfãos visíveis e restaurando o estado original de todos os demais POIs do mapa.

### Requirement: Cancelamento Seguro de Modos Interativos e Integridade do Ciclo de Vida da Cena
O `WidgetEditorMapas` SHALL cancelar e limpar proativamente todos os modos interativos temporários de desenho, medição e anotação (incluindo modo de polígono, traçado de novas rotas, modo de conversão de caixas, modo de linkagem e modo de câmera) e sobreposições visuais transitórias (como sobreposições de enquadramento de câmera em hover e em edição ativa) sempre que a cena gráfica for descarregada, recarregada ou quando o mapa ativo for alternado. O sistema SHALL garantir a integridade dos itens temporários descartados em memória, impedindo tentativas de acesso ou mutação a objetos gráficos C++ previamente destruídos pelo Qt e prevenindo exceções de ciclo de vida (`libshiboken`).

#### Scenario: Troca de mapa durante desenho de polígono
- **WHEN** o usuário ativar o modo de desenho de polígono em um mapa e subsequentemente selecionar outro mapa na lista lateral
- **THEN** o `WidgetEditorMapas` SHALL cancelar imediatamente o modo de desenho ativo, desativando cursores e descartando itens temporários de cena com segurança
- **AND** novos cliques na área do novo mapa não SHALL tentar acessar itens da cena anterior nem lançar exceções de runtime do Shiboken

#### Scenario: Recarregamento de mapa com clear de cena
- **WHEN** a cena gráfica for recarregada ou limpa através de `carregar_mapa`, `descarregar_mapa` ou `_renderizar_mapa` enquanto um modo interativo (desenho de polígono ou nova rota) estiver em andamento
- **THEN** o sistema SHALL cancelar com segurança o modo interativo antes ou durante a limpeza da cena
- **AND** a rotina de remoção de itens temporários SHALL verificar se os objetos gráficos subjacentes ainda são válidos antes de solicitar sua remoção à cena

#### Scenario: Tentativa de clique com item temporário descartado
- **WHEN** ocorrer um evento de mouse (`mousePressEvent`, `mouseMoveEvent`) em um estado de desenho cujo item gráfico temporário tenha sido invalidado em C++
- **THEN** o sistema SHALL identificar a perda de validade do item gráfico (`shiboken6.isValid() == False` ou divergência de cena) e abortar a operação ou reiniciar o item sem propagar erro fatal de execução

#### Scenario: Passagem de cursor sobre referência após limpeza ou recarregamento de cena
- **WHEN** uma sobreposição de enquadramento de câmera (`item_hover_camera_overlay`) tiver sido adicionada à cena e a cena for subsequentemente limpa via `cena.clear()`, troca de mapa ou descarregamento
- **THEN** o sistema SHALL invalidar e anular o ponteiro de sobreposição em Python
- **AND** na passagem subsequente do cursor do mouse sobre qualquer referência (com ou sem ajuste de câmera), o sistema SHALL verificar a validade do objeto em C++ e a pertinência à cena atual antes de qualquer chamada a métodos do item (como `setVisible`), recriando o item com segurança na cena ativa se necessário e impedindo exceções do Shiboken

#### Scenario: Entrada em modo de câmera após limpeza de cena
- **WHEN** a cena gráfica for limpa ou recriada após a utilização anterior do modo de câmera
- **THEN** o `WidgetEditorMapas` SHALL verificar a integridade física de `item_camera_overlay` via `shiboken6.isValid()` e correspondência de cena ativa antes de invocar qualquer mutação ou visibilidade, instanciando um novo item limpo na cena atual caso o anterior tenha sido destruído
