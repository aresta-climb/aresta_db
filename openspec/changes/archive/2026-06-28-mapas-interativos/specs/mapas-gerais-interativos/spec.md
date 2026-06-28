## ADDED Requirements

### Requirement: Coleção externa de mapas em Pico
O sistema MUST permitir que um `Pico` contenha referências a uma coleção de mapas interativos através do campo `mapas_gerais`.

#### Scenario: Abrindo o mapa geral no app
- **WHEN** o usuário abre o pico no aplicativo
- **THEN** o mapa geral é carregado interativamente com seus Pontos de Interesse e referências de roteamento ativas

### Requirement: Editor de croquis renderizando coleções de mapas
O Editor MUST identificar campos do tipo `ArquivoMapas` e instanciar botões de visualização na árvore.

#### Scenario: Acesso pelo Editor de Mapas
- **WHEN** o usuário clica em `mapas_gerais` no Editor de Croquis
- **THEN** um botão "Abrir no Editor de Mapas" será disponibilizado para desenhar ou iterar nos POIs do mapa geral
