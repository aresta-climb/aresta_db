## ADDED Requirements

### Requirement: Sincronização Estrutural Reativa e Validação de Mapa Ativo
O `WidgetEditorMapas` SHALL reagir imediatamente a alterações estruturais na lista de mapas do modelo (`CroquiModel`), incluindo adições e remoções de itens no campo `mapas`. Ao detectar remoção ou substituição de mapas, a interface SHALL reconstruir a lista lateral de mapas. Se o mapa atualmente exibido (`msg_mapa_proxy`) tiver sido removido ou não pertencer mais à árvore ativa do croqui, o `WidgetEditorMapas` SHALL descarregar a cena gráfica e o painel de referências, resetando a seleção. Além disso, antes de iniciar o desenho ou registrar novos elementos (POIs, linhas, nós, referências), o `WidgetEditorMapas` SHALL validar se o mapa atual ainda pertence à árvore ativa, bloqueando mutações órfãs.

#### Scenario: Remoção de mapa atualmente visualizado no editor
- **WHEN** um mapa selecionado no `WidgetEditorMapas` for removido da árvore do croqui por um comando do histórico
- **THEN** o `WidgetEditorMapas` SHALL detectar a remoção, atualizar a lista lateral de mapas, descarregar a cena gráfica e invalidar a referência ao mapa removido

#### Scenario: Tentativa de desenhar ou adicionar elementos em mapa não sincronizado
- **WHEN** o usuário tentar adicionar um POI, traçado ou referência sobre uma referência de mapa que não pertença à árvore ativa
- **THEN** o editor SHALL rejeitar a ação, emitir aviso visual e sincronizar a seleção com os mapas válidos existentes

#### Scenario: Restauração/Desfazer (Undo) da remoção de um mapa
- **WHEN** o usuário desfaz a remoção de um mapa no histórico
- **THEN** o `WidgetEditorMapas` SHALL atualizar a lista lateral incluindo o mapa restaurado e permitir sua seleção e edição normal
