## MODIFIED Requirements

### Requirement: Composição de Trechos em Referências
O sistema SHALL permitir que uma `Referencia` de escalada componha múltiplos elementos de linha e pontos de interesse através do campo `ids`, permitindo que vias e variantes compartilhem segmentos de traçado comuns, garantindo continuidade de curvatura suave nos pontos de transição e destaque unificado da rota completa.

#### Scenario: Seleção de Via com Trecho Compartilhado e Saída Própria
- **WHEN** uma referência lista `ids: ["trecho_base_comum", "trecho_fim_variante"]`
- **THEN** o sistema SHALL associar todos os segmentos à mesma entidade de escalada para fins de destaque unificado e navegação.

#### Scenario: Continuidade de Renderização em Segmentos Concatenados
- **WHEN** uma referência contém múltiplos segmentos de linha contíguos que compartilham nós extremos com as mesmas coordenadas
- **THEN** o sistema SHALL tratar a cadeia de nós de forma encadeada, preservando a suavidade visual da curva de interpolação na transição entre os segmentos.
