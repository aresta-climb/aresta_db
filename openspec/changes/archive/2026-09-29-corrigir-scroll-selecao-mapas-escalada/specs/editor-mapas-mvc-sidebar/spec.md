## ADDED Requirements

### Requirement: Seleção e retenção estrita de mapas de escalada na lista lateral
A lista lateral de mapas do editor MUST manter a seleção destacada no mapa de escalada individual selecionado, sem redefinir ou retroceder a seleção para o mapa do setor pai.

#### Scenario: Seleção direta de mapa de escalada
- **WHEN** o usuário seleciona um mapa pertencente a uma escalada na lista lateral
- **THEN** o mapa da escalada é exibido na visualização principal
- **THEN** o item correspondente à escalada permanece destacado na lista lateral

#### Scenario: Setor pai com mapa próprio
- **WHEN** um setor possui um ou mais mapas próprios e uma ou mais escaladas com mapas próprios
- **WHEN** o usuário seleciona o primeiro mapa de uma dessas escaladas
- **THEN** o item selecionado na lista lateral é exatamente o mapa da escalada e não o primeiro mapa do setor

### Requirement: Navegação contínua por teclado na lista de mapas
A navegação por teclado (tecla de seta para baixo / tecla de seta para cima) na lista lateral de mapas MUST progredir linearmente por todos os mapas listados (mapas gerais, de setor e de escaladas), sem entrar em ciclos ou retroceder para mapas anteriores.

#### Scenario: Navegar do mapa de setor para o mapa de escalada e subsequentes
- **WHEN** o foco está no último mapa de um setor
- **WHEN** o usuário pressiona a tecla de seta para baixo
- **THEN** a seleção visual avança para o primeiro mapa de escalada daquele setor
- **WHEN** o usuário pressiona a tecla de seta para baixo novamente
- **THEN** a seleção visual avança para o próximo mapa da lista sem retornar ao mapa do setor anterior

### Requirement: Rolagem automática da lista para o mapa ativo
O editor de mapas MUST garantir que qualquer mapa selecionado programaticamente ou via navegação externa fique visível na área de exibição da lista lateral.

#### Scenario: Foco em mapa fora da área visível
- **WHEN** um mapa de escalada ou setor distante do topo da lista é selecionado
- **THEN** a lista lateral rola automaticamente até tornar o item selecionado visível ao usuário
