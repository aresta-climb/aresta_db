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
O sistema SHALL fornecer um diálogo robusto para adição de novos mapas contendo botão explícito de seleção de arquivos, suporte a arrastar e soltar (drag & drop), painel de metadados ricos (dimensões, tamanho formatado e formato), pré-processamento WebP automático em RAM e validação de nomes e colisões em tempo real.

#### Scenario: Seleção de Arquivo com Exibição de Metadados e Pré-processamento
- **WHEN** o usuário seleciona ou arrasta um arquivo de imagem no diálogo de adição de mapa
- **THEN** o sistema SHALL exibir a pré-visualização gráfica, apresentar resolução ($W \times H$), tamanho e formato original nos metadados, e pré-processar os bytes para WebP.

#### Scenario: Validação de Conflito de Nomes em Tempo Real
- **WHEN** o usuário digita um nome de arquivo que já existe na memória RAM ou na pasta `imagens/` do disco
- **THEN** o sistema SHALL exibir um alerta visual imediato de colisão de nomes e desabilitar o botão de confirmação.

### Requirement: Ferramenta de Desenho e Edição de Traçados Vetoriais de Vias
O sistema SHALL fornecer uma ferramenta visual ("Nova Linha" / Caneta) no painel lateral do Editor de Mapas para permitir o desenho interativo de trajetos de vias e boulders diretamente sobre a imagem do mapa, calculando e exibindo a Spline Catmull-Rom em tempo real conforme os pontos são clicados.

#### Scenario: Início e Conclusão de Desenho de Linha
- **WHEN** o usuário clica no botão "Nova Linha", clica em múltiplos pontos da rocha na cena e confirma o término com duplo clique ou tecla Enter
- **THEN** o sistema SHALL criar um novo elemento visual do tipo `linha` com nós tipados (`CIRCULO_IDENTIFICADOR`, `PASSAGEM`, `TOP_PARADA`), calcular a curva suave na cena e registrar a adição no `CroquiModel` via `QUndoCommand`.

#### Scenario: Cancelamento do Desenho de Linha
- **WHEN** o usuário está no modo de desenho de linha e pressiona a tecla Esc ou botão direito sem nós suficientes
- **THEN** o sistema SHALL cancelar a operação, remover a linha temporária da cena e restaurar o cursor padrão de navegação.

### Requirement: Seletor de Cores de Alto Contraste para Elementos do Mapa
O sistema SHALL fornecer um seletor visual de cores no diálogo de edição e no menu de contexto dos elementos do mapa, disponibilizando uma paleta recomendada de alto contraste para rocha (Vermelho, Laranja, Amarelo, Verde Lima, Ciano, Roxo, Branco, Cinza) e opção de cor personalizada com suporte a `QUndoCommand`.

#### Scenario: Alteração de Cor de Traçado
- **WHEN** o usuário seleciona uma nova cor na paleta para uma linha ou POI existente
- **THEN** o sistema SHALL atualizar a cor da linha e de seus marcadores na cena imediatamente e registrar o comando de alteração de cor na pilha de histórico.

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

