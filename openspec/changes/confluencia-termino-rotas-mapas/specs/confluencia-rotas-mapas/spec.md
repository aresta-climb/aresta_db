## Purpose

Define os requisitos comportamentais e funcionais para a detecção de caminhos remanescentes, interface de popover contextual com ghost preview e fatiamento topológico atômico em confluências e términos de rotas no editor de mapas.

## ADDED Requirements

### Requirement: Descoberta Topológica de Continuações de Rotas
O sistema SHALL analisar o grafo de traçados e referências do mapa a partir de uma coordenada ou resultado de snap magnético, identificando todas as continuações possíveis até os respectivos topos ou ancoragens finais das rotas que compartilham o segmento interceptado.

#### Scenario: Descoberta de caminhos a montante a partir de nó intermediário
- **WHEN** o usuário realiza snap sobre um nó intermediário de uma linha associada a uma ou mais referências de escalada
- **THEN** o sistema SHALL extrair para cada referência a sequência ordenada de nós desde o ponto de snap até o nó final (topo), identificando o nome da via e o rótulo do nó de destino.

#### Scenario: Descoberta com bifurcações múltiplas adiante
- **WHEN** o trecho interceptado pertence a duas ou mais vias que se bifurcam mais adiante em topos diferentes
- **THEN** o sistema SHALL identificar separadamente cada ramificação como uma opção de continuação distinta com seu respectivo nome de escalada e topo.

#### Scenario: Snap em ponto de curva
- **WHEN** o snap magnético ocorre sobre um segmento de reta ou curva entre dois nós existentes
- **THEN** o sistema SHALL calcular o ponto de corte projetado e mapear a continuidade da rota a partir desse ponto até o topo.

### Requirement: Popover Contextual e Menu de Escolha de Confluência
O sistema SHALL exibir um popover contextual ancorado no ponto do clique sempre que o usuário clicar com snap magnético em um nó intermediário ou segmento de curva pertencente a rotas existentes com continuidade para a frente.

#### Scenario: Apresentação de opções de término e opção de apenas adicionar ponto
- **WHEN** o usuário clica sobre o ponto de snap de uma linha existente que possui continuidade até um topo
- **THEN** o sistema SHALL exibir um popover listando as rotas/topos alcançáveis (com atalhos numéricos como 1, 2) e a opção explícita de "Apenas adicionar ponto e continuar desenhando".

#### Scenario: Cancelamento seguro sem adicionar nós
- **WHEN** o popover está aberto e o usuário pressiona a tecla Esc ou clica fora da área do menu
- **THEN** o sistema SHALL fechar o popover sem inserir nenhum novo nó no traçado e sem modificar as rotas existentes.

#### Scenario: Confluência direta ao clicar em nó de topo
- **WHEN** o usuário clica com snap diretamente sobre o último nó (topo) de uma rota existente
- **THEN** o sistema SHALL conectar a nova rota àquele mesmo topo e finalizar o desenho imediatamente, sem abrir menu popover intermediário.

### Requirement: Pré-Visualização Dinâmica (Ghost Preview)
O sistema SHALL fornecer retorno visual em tempo real na cena gráfica projetando o traçado remanescente (ghost preview) correspondente à opção atualmente focada no popover.

#### Scenario: Destaque visual do traçado remanescente ao focar uma opção
- **WHEN** o usuário navega com o teclado (setas para cima/baixo) ou passa o cursor do mouse sobre uma opção de término de rota no popover
- **THEN** o sistema SHALL renderizar na cena gráfica uma linha translúcida destacada em verde acompanhando o caminho exato do ponto de confluência até o topo correspondente.

#### Scenario: Ocultação do ghost preview ao focar opção neutra ou fechar popover
- **WHEN** o usuário foca a opção "Apenas adicionar ponto" ou o popover é fechado/cancelado
- **THEN** o sistema SHALL remover imediatamente a linha de pré-visualização da cena gráfica.

### Requirement: Fatiamento Topológico e Recomposição de Referências
O sistema SHALL fatiar automaticamente o traçado interceptado e atualizar as referências relacionais no modelo Protobuf de forma atômica e consistente com as regras semânticas de topos e histórico.

#### Scenario: Fatiamento automático em nó existente e atualização de referências
- **WHEN** o usuário confirma a opção de confluência em um nó intermediário existente
- **THEN** o sistema SHALL dividir a linha existente no nó em duas sublinhas contíguas, atualizar todas as referências que continham a linha original para a sequência das sublinhas, e criar a referência da nova rota contendo seu trecho exclusivo seguido pelas sublinhas restantes até o topo escolhido.

#### Scenario: Fatiamento automático em curva com inserção de nó
- **WHEN** o usuário confirma a opção de confluência em um ponto de curva
- **THEN** o sistema SHALL inserir um novo nó de tipo PASSAGEM no ponto de projeção, dividir a linha em duas sublinhas a partir desse novo nó e atualizar as referências correspondentes.

#### Scenario: Desambiguação de topos e reversibilidade atômica via Undo
- **WHEN** a confluência é concluída e duas ou mais vias convergem no mesmo topo
- **THEN** o sistema SHALL atualizar os rótulos de topo conforme as regras semânticas de desambiguação e agrupar todas as operações de mutação em um único comando de histórico na pilha QUndoStack, permitindo reversão total com um único comando Desfazer (Ctrl+Z).
