# editor-mapas Specification Delta

## ADDED Requirements

### Requirement: Ferramenta de Desenho e Edição de Traçados Vetoriais de Vias
O sistema SHALL fornecer uma ferramenta visual ("Nova Linha" / Caneta) no painel lateral do Editor de Mapas para permitir o desenho interativo de trajetos de vias e boulders diretamente sobre a imagem do mapa, calculando e exibindo a Spline Catmull-Rom em tempo real conforme os pontos são clicados.

#### Scenario: Início e Conclusão de Desenho de Linha
- **WHEN** o usuário clica no botão "Nova Linha", clica em múltiplos pontos da rocha na cena e confirma o término com duplo clique ou tecla Enter
- **THEN** o sistema SHALL criar um novo elemento visual do tipo `linha` com nós tipados (`INICIO_BASE`, `PASSAGEM`, `TOP_PARADA`), calcular a curva suave na cena e registrar a adição no `CroquiModel` via `QUndoCommand`.

#### Scenario: Cancelamento do Desenho de Linha
- **WHEN** o usuário está no modo de desenho de linha e pressiona a tecla Esc ou botão direito sem nós suficientes
- **THEN** o sistema SHALL cancelar a operação, remover a linha temporária da cena e restaurar o cursor padrão de navegação.

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
