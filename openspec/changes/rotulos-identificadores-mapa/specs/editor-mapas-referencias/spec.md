## ADDED Requirements

### Requirement: Preview de Codenome no Card da Referência
O `CardReferencia` no painel de referências do Editor de Mapas SHALL exibir um preview visual do codenome resultante da referência calculado a partir dos nós identificadores e labels dos pontos de interesse associados.

#### Scenario: Referência com identificadores válidos
- **WHEN** uma referência possui pontos ou linhas com círculos identificadores válidos (ex: "5" e "C")
- **THEN** o card da referência SHALL exibir uma pílula/badge indicando o codenome (ex: "Codenome: [ 5-C ]")

#### Scenario: Referência sem identificadores
- **WHEN** uma referência possui apenas traços sem círculos ou pontos com label vazio
- **THEN** o card da referência SHALL exibir um indicativo visual de aviso "Sem rótulo" com explicação de que o aplicativo não exibirá identificador

### Requirement: Inversão Rápida da Ordem dos IDs Linkados
O Editor de Mapas SHALL disponibilizar uma ação direta no card da referência para inverter a lista ordenada de `ids`, registrando a operação na pilha de histórico de Undo/Redo.

#### Scenario: Invertendo a sequência dos traços com um clique
- **WHEN** o usuário clica no botão "Inverter Ordem" de uma referência com IDs `['linha_21', 'linha_18', 'linha_9', 'linha_16', 'linha_12']`
- **THEN** o sistema SHALL inverter a lista de IDs para `['linha_12', 'linha_16', 'linha_9', 'linha_18', 'linha_21']` através de um comando `QUndoCommand`
- **AND** o preview do codenome no card da referência SHALL ser recalculado e atualizado imediatamente

### Requirement: Desfazer e Refazer da Inversão de IDs
A ação de inversão de ordem dos IDs SHALL respeitar estritamente a reversibilidade pelo mecanismo global de histórico (`Ctrl+Z` / `Ctrl+Y`).

#### Scenario: Desfazendo inversão de IDs
- **WHEN** o usuário aciona o comando Desfazer (Ctrl+Z) após inverter a ordem dos IDs de uma referência
- **THEN** a lista de IDs da referência no mapa SHALL retornar ao estado imediatamente anterior à inversão
