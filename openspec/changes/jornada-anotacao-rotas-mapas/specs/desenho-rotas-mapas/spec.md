## Purpose

Define a especificação funcional e de comportamento do fluxo de criação e anotação de rotas em mapas de escalada, incluindo seleção de vias existentes, criação inline, snap magnético ponto a ponto, fatiamento automático de traçados compartilhados, convenção semântica com desambiguação de TOP, escopo unificado de numeração por setor com IDs disjuntos e substituição do fluxo legado de linha desconectada.

## ADDED Requirements

### Requirement: Seleção e Criação Rápida de Rotas no Editor de Mapas
O sistema SHALL fornecer uma ação rápida "+ Nova Rota" no Editor de Mapas que exibe uma paleta com foco imediato no teclado, permitindo selecionar uma escalada pré-existente do setor que ainda não possui traçado no mapa ou criar uma nova escalada (nome, tipo e grau opcional) inline antes de iniciar o traçado.

#### Scenario: Seleção de escalada existente sem traçado
- **WHEN** o usuário aciona "+ Nova Rota" e seleciona uma escalada já cadastrada no setor atual
- **THEN** o sistema SHALL vincular o traçado subsequente a essa escalada e ativar o modo de desenho na cena do mapa.

#### Scenario: Criação inline de nova escalada
- **WHEN** o usuário digita o nome de uma nova escalada inexistente no setor e confirma a criação
- **THEN** o sistema SHALL registrar a nova escalada na coleção do setor e iniciar imediatamente o modo de desenho na cena do mapa.

### Requirement: Substituição do Botão e Fluxo Legado de Linha
O sistema SHALL remover o botão legado "Nova Linha / Escalada" e seu respectivo fluxo de criação de linha desconectada com popup manual de identificador no Editor de Mapas, canalizando toda criação de traçado através do fluxo "+ Nova Rota".

#### Scenario: Ausência do botão legado na interface
- **WHEN** o Editor de Mapas é renderizado
- **THEN** o sistema SHALL exibir o botão primário "+ Nova Rota" e SHALL NOT exibir o botão legado "Nova Linha / Escalada".

#### Scenario: Tentativa de desenho direto sem rota
- **WHEN** o usuário deseja traçar uma via
- **THEN** o sistema SHALL exigir a identificação ou seleção prévia da escalada via paleta de rota, prevenindo a criação de traçados órfãos sem referência.

### Requirement: Modo de Desenho com Snap Magnético Ponto a Ponto
O sistema SHALL permitir o desenho do traçado da via na cena do mapa através de cliques ponto a ponto, fornecendo atração magnética visual e geométrica (snap) quando o cursor estiver próximo a nós existentes ou ao longo do corpo de linhas de traçado vizinhas.

#### Scenario: Snap magnético em nó de traçado existente
- **WHEN** o cursor do mouse se aproxima de um nó de uma linha existente a uma distância de tolerância (ex: até 15 pixels)
- **THEN** o sistema SHALL destacar visualmente o nó alvo e alinhar o ponto do traçado exatamente nas coordenadas daquele nó ao clicar.

#### Scenario: Snap magnético e inserção de nó no meio de um traçado existente
- **WHEN** o usuário clica sobre o segmento ou curva de uma linha existente em um ponto onde não há nó prévio
- **THEN** o sistema SHALL projetar o ponto na geometria da linha existente e inserir um novo nó de bifurcação exatamente na posição correspondente.

### Requirement: Fatiamento Automático de Traçados ("Sticky")
O sistema SHALL fatiar automaticamente linhas existentes em subpartes reaproveitáveis sempre que uma nova rota compartilhar um trecho (início, meio ou fim) ou bifurcar a partir de um ponto de uma linha existente, preservando as referências anteriores intactas.

#### Scenario: Fatiamento por bifurcação de variante
- **WHEN** uma nova rota conecta e percorre parte de uma linha existente e depois bifurca para a rocha livre
- **THEN** o sistema SHALL dividir a linha existente no ponto de bifurcação em um segmento comum e um segmento exclusivo da rota original, atualizando a referência da rota original para conter ambos os segmentos em ordem e incluindo o segmento comum na referência da nova rota.

#### Scenario: Sincronização de nós soldados
- **WHEN** um nó de junção compartilhado entre duas ou mais linhas é movido pelo usuário
- **THEN** o sistema SHALL atualizar a posição correspondente em todas as linhas conectadas naquele ponto simultaneamente.

### Requirement: Convenção Semântica de Início, Saídas e Marcadores
O sistema SHALL aplicar automaticamente a convenção semântica de marcação em nós de traçado: números sequenciais para inícios (`1`, `2`, `3`...), rotulagem combinada para saídas compartilhadas (`1, 2`), e suporte a marcadores geométricos (`▲`, `★`, `■`) em nós intermediários notáveis.

#### Scenario: Atribuição automática de próximo número de início
- **WHEN** uma nova rota independente é iniciada a partir do chão
- **THEN** o sistema SHALL configurar o nó inicial como círculo identificador com o próximo número sequencial disponível no setor.

#### Scenario: Rotulagem de saída compartilhada
- **WHEN** uma nova rota compartilha o nó de início de uma rota existente com rótulo "1"
- **THEN** o sistema SHALL atualizar o rótulo do nó inicial compartilhado para "1, 2".

### Requirement: Numeração Consistente e IDs Disjuntos no Escopo do Setor
O sistema SHALL gerenciar números identificadores de início e IDs de pontos de interesse no escopo unificado de todos os mapas pertencentes ao mesmo setor, reutilizando o número identificador quando a mesma escalada for desenhada em mais de um mapa e gerando IDs de POI mutuamente disjuntos entre todos os mapas do setor.

#### Scenario: Reutilização de número para escalada mapeada em outro mapa do setor
- **WHEN** uma escalada que já possui início identificado como "2" em um mapa do setor for anotada em outro mapa do mesmo setor
- **THEN** o sistema SHALL reutilizar o identificador "2" no nó de início do novo mapa para manter a consistência entre perspectivas.

#### Scenario: Próximo número sequencial abrangendo todos os mapas do setor
- **WHEN** uma nova escalada for criada em um setor cujos mapas existentes já utilizem os números "1", "2" e "3"
- **THEN** o sistema SHALL sugerir o número "4" para a nova escalada, independentemente de qual mapa do setor estiver ativo.

#### Scenario: Geração de IDs de POI disjuntos entre mapas do mesmo setor
- **WHEN** novos pontos de interesse e linhas de traçado forem gerados em qualquer mapa do setor
- **THEN** o sistema SHALL atribuir IDs únicos que não coincidam com nenhum outro ID de POI existente em nenhum mapa daquele setor.

### Requirement: Desambiguação Inteligente de TOP sob Demanda
O sistema SHALL omitir círculos identificadores no final de rotas isoladas e criar círculos de TOP com letras sequenciais (`A`, `B`, `C`...) exclusivamente para desambiguar rotas quando duas ou mais escaladas terminarem em topos distintos após bifurcação ou convergirem no mesmo final.

#### Scenario: Rota isolada sem círculo de TOP
- **WHEN** uma rota é criada sem compartilhar linhas ou finais com outras rotas
- **THEN** o sistema SHALL encerrar o traçado no topo sem criar círculo identificador ou marcador visual de TOP.

#### Scenario: Desambiguação retroativa de finais em bifurcação
- **WHEN** uma nova rota bifurca de uma rota original que não possuía círculo de TOP e ambas terminam em topos distintos
- **THEN** o sistema SHALL converter o nó final da rota original em círculo identificador com a letra "A" e o nó final da nova rota em círculo identificador com a letra "B".

#### Scenario: Convergência no mesmo TOP
- **WHEN** uma nova rota termina conectando no mesmo nó final de uma rota existente
- **THEN** o sistema SHALL identificar o nó final comum com um círculo identificador com a mesma letra de final.

### Requirement: Atomicidade e Reversibilidade de Mutações via Histórico
Toda criação de rota, incluindo a adição da escalada, divisão de linhas existentes, criação de novas linhas, atualização de referências e atribuição de marcadores, SHALL ser agrupada em um único macro no histórico (`QUndoCommand`), permitindo desfazer ou refazer toda a operação de forma atômica.

#### Scenario: Desfazer atômico de rota com fatiamento
- **WHEN** o usuário aciona "Desfazer" (Ctrl+Z) imediatamente após concluir uma nova rota que fatiou uma linha existente
- **THEN** o sistema SHALL remover a nova rota e a nova escalada, reconstituir a linha original inteira e restaurar os marcadores anteriores de início e fim.
