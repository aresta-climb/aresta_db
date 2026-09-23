## ADDED Requirements

### Requirement: Robustez Topológica em Fatiamento de Travessias
O sistema SHALL validar estritamente a existência de pelo menos dois nós intermediários distintos ao identificar uma travessia compartilhada em linha existente, garantindo que o índice de entrada seja estritamente menor que o índice de saída e que ambos pertençam ao intervalo intermediário da linha original.

#### Scenario: Rota com duplo clique sobre nó intermediário existente
- **WHEN** o usuário finaliza uma nova rota com duplo clique sobre o mesmo nó intermediário de uma linha existente gerando múltiplos pontos coincidentes
- **THEN** o sistema SHALL reconhecer que não há segmento intermediário percorrido com múltiplos nós distintos e NÃO DEVE disparar o fatiamento triplo com índices de entrada e saída idênticos.

#### Scenario: Rota com travessia compartilhando nós intermediários válidos
- **WHEN** uma nova rota conecta a uma linha existente em um nó intermediário A e sai em um nó intermediário B posterior (onde 0 < A < B < N - 1)
- **THEN** o sistema SHALL fatiar a linha em três sublinhas válidas, mantendo no mínimo dois nós em cada trecho resultante e associando o trecho compartilhado à nova rota.

### Requirement: Sanitização de Pontos Duplicados em Traçados
O sistema SHALL sanitizar a lista de pontos coletados durante a criação de novos traçados antes de submetê-la ao controlador de mapas, eliminando pontos consecutivos idênticos ou com separação menor que a tolerância de clique.

#### Scenario: Duplo clique ao concluir traçado de rota
- **WHEN** o usuário conclui o traçado de uma nova rota utilizando duplo clique no mouse
- **THEN** o sistema SHALL descartar o ponto redundante gerado no mesmo local pelo primeiro clique do evento duplo, gerando um traçado sem nós com distância zero.

### Requirement: Fallback Resiliente em Adição de Traçados com Topologia Complexa
O sistema SHALL incorporar tratamento de exceções na camada de controle durante a análise topológica de sobreposição, assegurando que eventuais falhas no fatiamento revertam graciosamente para a criação da linha como traçado independente sem interromper o fluxo do usuário ou emitir erros não tratados.

#### Scenario: Falha inesperada durante tentativa de fatiamento topológico
- **WHEN** a análise topológica encontra uma inconsistência nos índices ou geometria durante o cálculo de fatiamento
- **THEN** o sistema SHALL registrar aviso em log e adicionar o traçado da nova rota pelo fluxo padrão simples sem fatiar a linha existente, preservando o estado do croqui.
