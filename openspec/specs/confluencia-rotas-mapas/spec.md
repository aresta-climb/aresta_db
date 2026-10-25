# confluencia-rotas-mapas Specification

## Purpose

Define os requisitos comportamentais e funcionais para a detecção de caminhos remanescentes com deduplicação, interface de popover contextual com ghost preview e fatiamento topológico atômico em confluências e términos conjuntos de rotas no editor de mapas.

## Requirements

### Requirement: Descoberta Topológica de Continuações de Rotas
O sistema SHALL analisar o grafo de traçados (`PontoDeInteresse.uid`) e referências (`Referencia.pontos_uids` e `alvo_uid`) do mapa a partir de um resultado de snap magnético, identificando todas as continuações possíveis até os respectivos topos ou ancoragens finais das rotas que compartilham o segmento interceptado.

#### Scenario: Descoberta de caminhos a montante a partir de nó intermediário ou junção
- **WHEN** o usuário realiza snap sobre um nó intermediário de uma linha ou sobre um nó de junção entre sublinhas pertencente a uma ou mais referências de escalada
- **THEN** o sistema SHALL extrair para cada caminho distinto a sequência ordenada de coordenadas e `pontos_uids` desde o ponto de snap até o nó final (topo), identificando os nomes das vias associadas e o rótulo do nó de destino.

#### Scenario: Descoberta com bifurcações múltiplas adiante
- **WHEN** o trecho interceptado pertence a duas ou mais vias que se bifurcam mais adiante em sequências de segmentos ou topos diferentes
- **THEN** o sistema SHALL identificar separadamente cada ramificação como uma opção de continuação distinta com seu respectivo nome de escalada e rótulo de topo.

#### Scenario: Deduplicação de caminhos remanescentes idênticos
- **WHEN** duas ou mais referências passam pelo ponto interceptado e compartilham exatamente a mesma sequência remanescente de `pontos_uids` até o mesmo topo
- **THEN** o sistema SHALL agrupar essas referências em uma única opção de continuação exibindo os nomes das vias combinados, evitando opções duplicadas para o mesmo caminho físico.

#### Scenario: Snap em ponto de curva
- **WHEN** o snap magnético ocorre sobre um segmento de reta ou curva entre dois nós existentes
- **THEN** o sistema SHALL calcular o ponto de corte projetado e mapear a continuidade da rota a partir desse ponto até o topo.

### Requirement: Popover Contextual e Menu de Escolha de Confluência
O sistema SHALL exibir um popover contextual ancorado no ponto do clique sempre que o usuário, já tendo adicionado pelo menos um ponto prévio na nova rota, clicar com snap magnético em um nó intermediário, junção de sublinhas ou segmento de curva pertencente a rotas existentes com continuidade para a frente.

#### Scenario: Guarda do primeiro clique na base da rota
- **WHEN** a nova rota ainda não possui nenhum ponto adicionado (`len(pontos_nova_rota) == 0`) e o usuário clica com snap sobre qualquer nó ou linha existente
- **THEN** o sistema SHALL adicionar apenas o ponto inicial da nova rota sem abrir o popover de confluência, permitindo iniciar saídas compartilhadas normalmente.

#### Scenario: Apresentação de opções de término com primeira opção pré-selecionada
- **WHEN** a nova rota já possui pelo menos um ponto e o usuário clica sobre um ponto de snap com continuidade até um ou mais topos
- **THEN** o sistema SHALL exibir um popover listando os caminhos alcançáveis (com atalhos numéricos `1`, `2`... e a primeira opção pré-selecionada para confirmação rápida com `Enter`) seguido pela opção "Apenas adicionar ponto e continuar desenhando".

#### Scenario: Cancelamento seguro sem adicionar nós
- **WHEN** o popover está aberto e o usuário pressiona a tecla `Esc` ou clica fora da área do menu
- **THEN** o sistema SHALL fechar o popover sem inserir nenhum novo nó no traçado em andamento e sem modificar as rotas existentes.

#### Scenario: Confluência direta ao clicar no nó de topo final real
- **WHEN** a nova rota já possui pelo menos um ponto e o usuário clica com snap diretamente sobre o último nó da última sublinha de uma rota existente (sem nenhum segmento subsequente na referência)
- **THEN** o sistema SHALL conectar a nova rota àquele mesmo topo e finalizar o desenho imediatamente, sem abrir o menu popover intermediário.

### Requirement: Pré-Visualização Dinâmica (Ghost Preview)
O sistema SHALL fornecer retorno visual em tempo real na cena gráfica projetando o traçado remanescente (ghost preview) correspondente à opção atualmente focada no popover.

#### Scenario: Destaque visual imediato e ao navegar pelas opções
- **WHEN** o popover é aberto (com a primeira opção pré-selecionada) ou quando o usuário navega com o teclado (setas para cima/baixo) ou passa o cursor do mouse sobre uma opção de término de rota
- **THEN** o sistema SHALL renderizar na cena gráfica uma curva spline translúcida destacada em verde acompanhando o caminho exato do ponto de confluência até o topo correspondente.

#### Scenario: Ocultação do ghost preview ao focar opção neutra ou fechar popover
- **WHEN** o usuário foca a opção "Apenas adicionar ponto e continuar desenhando" ou quando o popover é fechado/cancelado
- **THEN** o sistema SHALL remover de forma segura o item gráfico de pré-visualização da cena.

### Requirement: Fatiamento Topológico e Recomposição de Referências
O sistema SHALL fatiar o traçado interceptado quando necessário e atualizar as referências relacionais (`pontos_uids` e `alvo_uid`) no modelo Protobuf de forma atômica e consistente com as regras semânticas de topos e histórico.

#### Scenario: Fatiamento automático em nó intermediário e atualização de referências
- **WHEN** o usuário confirma a confluência em um nó estritamente intermediário (`0 < indice_no < total_nos - 1`) de uma linha existente
- **THEN** o sistema SHALL dividir a linha existente no nó em duas sublinhas contíguas com novos UIDs NanoID disjuntos, atualizar os `pontos_uids` de todas as referências que continham a linha original para a sequência das duas sublinhas, e criar a referência da nova rota contendo o UID do seu trecho exclusivo seguido pelo UID da segunda sublinha e eventuais sublinhas subsequentes até o topo escolhido.

#### Scenario: Fatiamento automático em curva com inserção de nó
- **WHEN** o usuário confirma a confluência em um ponto de curva
- **THEN** o sistema SHALL inserir um novo nó de tipo `PASSAGEM` no ponto de projeção, dividir a linha em duas sublinhas a partir desse novo nó e atualizar os `pontos_uids` das referências correspondentes.

#### Scenario: Reconexão em junção existente entre sublinhas sem re-fatiamento
- **WHEN** o usuário confirma a confluência exatamente sobre o primeiro nó (`indice_no == 0`) de uma sublinha ou sobre o último nó (`indice_no == total_nos - 1`) de uma sublinha que possui sublinhas subsequentes na referência
- **THEN** o sistema SHALL conectar o trecho exclusivo da nova rota diretamente às coordenadas desse nó e herdar os `pontos_uids` subsequentes da referência sem fatiar novamente as linhas já divididas.

#### Scenario: Desambiguação de topos e reversibilidade atômica via Undo
- **WHEN** a confluência é concluída e duas ou mais vias passam a compartilhar traçado ou convergir no mesmo topo
- **THEN** o sistema SHALL atualizar os rótulos de topo via `desambiguar_topos` e agrupar todas as operações de mutação em um único macro na pilha `QUndoStack`, permitindo reversão integral com um único comando Desfazer (`Ctrl+Z`).
