# Spec Delta

## RENAMED Requirements
- FROM: `### Requirement: Linkagem Interativa de Formas`
- TO: `### Requirement: Vinculação Interativa de Elementos`

## MODIFIED Requirements

### Requirement: Vinculação Interativa de Elementos
O sistema SHALL fornecer um modo de interação de mouse ("Modo Vinculação") acionado pelo botão "Vincular Elementos" no card para associar ou desassociar elementos gráficos (pontos de interesse e trajetos) à Referência ativa.

#### Scenario: Adicionando IDs à referência
- **WHEN** no modo de Vinculação, o usuário clica sobre um elemento do mapa não vinculado
- **THEN** o ID da forma é adicionado à lista de IDs da Referência no painel e destacado em ciano imediatamente

#### Scenario: Entrada em modo de vinculação
- **WHEN** o usuário ativa o botão "Vincular Elementos" em um card de referência
- **THEN** a barra superior de aviso exibe orientações em português sobre o modo de vinculação
- **THEN** o card correspondente é selecionado no painel lateral
- **THEN** todos os elementos já vinculados à referência são destacados em ciano imediatamente no mapa

#### Scenario: Vinculação de elemento não associado
- **WHEN** no modo de Vinculação, o usuário clica sobre um elemento do mapa que não pertença à referência ativa
- **THEN** o ID do elemento é adicionado à lista de IDs da referência ativa
- **THEN** o elemento passa a ser destacado em ciano imediatamente no mapa

#### Scenario: Desvinculação de elemento já associado (Toggle)
- **WHEN** no modo de Vinculação, o usuário clica sobre um elemento do mapa que já pertença à referência ativa
- **THEN** o ID do elemento é removido da lista de IDs da referência ativa
- **THEN** o destaque em ciano do elemento é removido imediatamente no mapa

### Requirement: Seleção Persistente de Referência no Painel Lateral
The system SHALL permitir que o usuário selecione uma referência clicando sobre o seu card no painel direito, mantendo a seleção ativa e destacando persistentemente no mapa os elementos vinculados sem reter estados de vinculação anteriores no fallback de restauração.

#### Scenario: Seleção de card de referência por clique
- **WHEN** o usuário clica com o botão esquerdo sobre a área do card de referência no painel lateral
- **THEN** o card é marcado com estilo visual selecionado e todos os POIs vinculados àquela referência são destacados persistentemente em ciano no mapa

#### Scenario: Manutenção do destaque após saída do cursor
- **WHEN** uma referência está selecionada no painel lateral e o usuário move o cursor do mouse para o mapa ou para fora do painel
- **THEN** os POIs vinculados à referência selecionada permanecem destacados em ciano no visualizador do mapa

#### Scenario: Pré-visualização temporária por hover com restauração da seleção
- **WHEN** uma referência A está selecionada e o usuário move o cursor sobre o card de uma referência B
- **THEN** os POIs da referência B são destacados temporariamente no mapa
- **WHEN** o cursor deixa o card da referência B
- **THEN** o sistema restaura imediatamente o destaque dos POIs da referência selecionada A, sem restaurar referências de vinculações anteriores

#### Scenario: Alternância e desmarcação da referência ativa
- **WHEN** o usuário clica sobre o card da referência que já se encontra selecionada, ou clica no fundo neutro do mapa
- **THEN** a seleção da referência é cancelada, o card retorna ao estado visual padrão e o destaque em ciano é removido dos POIs
