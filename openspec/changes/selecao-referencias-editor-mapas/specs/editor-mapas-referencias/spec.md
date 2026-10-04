# Spec Delta

## ADDED Requirements

### Requirement: Seleção Persistente de Referência no Painel Lateral
O sistema SHALL permitir que o usuário selecione uma referência clicando sobre o seu card no painel direito, mantendo a seleção ativa e destacando persistentemente no mapa os pontos de interesse vinculados.

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
- **THEN** o sistema restaura imediatamente o destaque dos POIs da referência selecionada A

#### Scenario: Alternância e desmarcação da referência ativa
- **WHEN** o usuário clica sobre o card da referência que já se encontra selecionada, ou clica no fundo neutro do mapa
- **THEN** a seleção da referência é cancelada, o card retorna ao estado visual padrão e o destaque em ciano é removido dos POIs

### Requirement: Seleção Bidirecional a partir de POIs do Mapa
O sistema SHALL sincronizar a seleção de referências ao interagir com pontos de interesse no visualizador de mapas em modo normal, localizando e ativando automaticamente o card correspondente no painel lateral.

#### Scenario: Clique em POI vinculado a referência
- **WHEN** em modo normal (fora do modo de linkagem ou desenho), o usuário clica sobre um POI no mapa que pertença aos IDs de uma referência do mapa ativo
- **THEN** o sistema localiza a referência correspondente, ativa o estado selecionado em seu card no painel lateral, rola a lista de cards para torná-lo visível e mantém seus POIs destacados em ciano
