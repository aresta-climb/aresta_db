## MODIFIED Requirements

### Requirement: Centralização das Referências no Mapa
O sistema SHALL agrupar todas as referências de escalada/pontos de interesse no próprio objeto `Mapa` usando a estrutura `Referencia`, e não nas entidades (`Boulder`, `ViaEsportiva`, `Setor`, etc.). A migração SHALL garantir a integridade dos dados validando a existência dos pontos.

#### Scenario: Leitura de Referência Genérica
- **WHEN** o sistema processa um `Mapa`
- **THEN** ele lê a lista de `referencias` para saber quais pontos do mapa representam quais entidades

#### Scenario: Validação Estrita de Pontos na Migração
- **WHEN** a migração extrai os IDs de uma via
- **THEN** a referência SÓ é adicionada ao mapa se o mapa tiver todos os IDs desenhados em sua lista de `pontos_de_interesse`

## ADDED Requirements

### Requirement: Parsing de IDs Compostos e Distribuídos
O sistema de migração SHALL aplicar parsing hierárquico nos valores antigos de `id_no_mapa`: quebrando primeiro pelo separador `/` para distribuir ordenadamente aos mapas, e depois extraindo sequências alfanuméricas misturadas (letras e números juntos, ex: "2B") para transformá-los em múltiplos IDs distintos.

#### Scenario: Distribuição de Barra Estrita
- **WHEN** uma via possui `id_no_mapa: 1A/2B`
- **THEN** o grupo `1A` é testado SOMENTE contra o primeiro mapa, e o grupo `2B` é testado SOMENTE contra o segundo mapa

#### Scenario: Quebra de Letras e Números
- **WHEN** o valor extraído for a string `"1A"`
- **THEN** a string é quebrada para a lista `["1", "A"]` antes de validar com o mapa
