## ADDED Requirements

### Requirement: Centralização das Referências no Mapa
O sistema SHALL agrupar todas as referências de escalada/pontos de interesse no próprio objeto `Mapa` usando a estrutura `Referencia`, e não nas entidades (`Boulder`, `ViaEsportiva`, `Setor`, etc.).

#### Scenario: Leitura de Referência Genérica
- **WHEN** o sistema processa um `Mapa`
- **THEN** ele lê a lista de `referencias` para saber quais pontos do mapa representam quais entidades

### Requirement: Escopo Implícito e Explícito de Referências
O sistema SHALL assumir que uma `Referencia` apontando para uma `escalada` (sem definir `setor` ou `grupo`) pertence ao Setor em que o `Mapa` está aninhado. Para mapas de nível hierárquico superior (ex: Grupo), referenciar uma escalada exige prover o nome do Setor.

#### Scenario: Referência em Mapa de Setor
- **WHEN** a referência possui `escalada` preenchida e está dentro do YAML de um Setor
- **THEN** o sistema resolve a referência para a escalada daquele setor com o nome exato

#### Scenario: Referência em Mapa de Grupo (Cross-link/Falta de escopo)
- **WHEN** um mapa na raiz de um Grupo tenta referenciar uma escalada sem prover o campo `setor`
- **THEN** o validador do YAML/deploy SHALL emitir um warning indicando que a referência é ambígua

### Requirement: Geometria Ilimitada de Rota
O sistema SHALL usar uma lista ordenada de `ids` (repeated string) na Referência para definir o caminho de uma escalada no mapa, removendo a restrição de apenas início, meio e fim.

#### Scenario: Renderização de Rota Longa
- **WHEN** a referência possui 5 IDs de POIs
- **THEN** o sistema as trata como um caminho ordenado interligando os 5 pontos em sequência

### Requirement: Ajuste Fino de Câmera
O sistema SHALL permitir que cada referência sobrescreva o comportamento padrão de foco da câmera quando essa escalada for selecionada via interface.

#### Scenario: Foco Específico
- **WHEN** a referência define `AjusteDeCamera` com `posicao_vertical = 60`
- **THEN** a interface de renderização deve centralizar a referência de modo que ela fique a 60% da tela (acima do meio)
