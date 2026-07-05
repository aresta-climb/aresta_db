## ADDED Requirements

### Requirement: Bloqueio de arrasto de POI no modo linkagem
O sistema SHALL desabilitar a capacidade de arrastar (mover) os Pontos de Interesse (POIs) enquanto o modo de linkagem estiver ativo, permitindo que apenas eventos de seleção e clique sejam computados.

#### Scenario: Clicando em um POI no modo linkagem
- **WHEN** o usuário ativa o modo de linkagem e clica (ou clica e arrasta) sobre um POI
- **THEN** o POI é selecionado para a linkagem (se aplicável), mas sua posição na cena não é alterada em hipótese alguma.

#### Scenario: Desativando o modo linkagem
- **WHEN** o usuário sai do modo de linkagem
- **THEN** os POIs restauram sua capacidade original de serem movidos (arrastados) livremente pela cena.
