## ADDED Requirements

### Requirement: Hit-Testing Estrito em Traçados Vetoriais
O sistema SHALL restringir a área clicável e de seleção de uma linha de traçado vetorial exclusivamente à vizinhança imediata do seu traçado geométrico (stroke com tolerância controlada), desconsiderando completamente o espaço interno côncavo delimitado pelos nós extremos da curva aberta.

#### Scenario: Clique diretamente sobre o traçado da curva
- **WHEN** o usuário clica com o mouse a uma distância menor ou igual à tolerância de clique (ex: até 7px do traçado da curva)
- **THEN** o sistema SHALL registrar a colisão com a linha de traçado correspondente e marcá-la como selecionada.

#### Scenario: Clique no espaço vazio entre os extremos de uma curva aberta
- **WHEN** o usuário clica com o mouse em uma área que fica no interior do polígono imaginário formado entre os extremos de uma curva côncava ou travessia, mas a uma distância maior que a tolerância do traçado
- **THEN** o sistema SHALL ignorar a colisão com essa curva, permitindo que cliques atinjam elementos posicionados nessa região (como nós, outras vias ou o fundo do mapa).

#### Scenario: Seleção de nó de outra via posicionado na área vazia da curva
- **WHEN** o usuário clica sobre um nó ou elemento de outra via posicionado no vão interno de uma curva de travessia
- **THEN** o sistema SHALL selecionar o nó ou elemento clicado, sem que a curva de travessia vizinha intercepte o clique.

### Requirement: Destaque Visual da Curva Selecionada
O sistema SHALL renderizar a seleção de uma linha de traçado vetorial através de um halo luminoso ou contorno de destaque de alto contraste ao longo do próprio spline da curva, sem exibir caixas delimitadoras retangulares tracejadas nativas ao redor do item.

#### Scenario: Exibição de destaque em linha selecionada
- **WHEN** uma linha de traçado vetorial está no estado selecionado
- **THEN** o sistema SHALL desenhar um contorno/halo suave de destaque acompanhando todo o traçado da curva e ocultar a caixa delimitadora retangular padrão do Qt.

#### Scenario: Deseleção de linha de traçado
- **WHEN** a linha de traçado perde a seleção
- **THEN** o sistema SHALL remover o halo de destaque e restaurar a renderização padrão de traço da linha.
