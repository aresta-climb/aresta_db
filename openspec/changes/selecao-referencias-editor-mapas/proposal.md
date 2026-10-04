# Proposal

## Why

Atualmente no Editor de Mapas, as referências exibidas no painel direito (`PainelReferencias`) possuem apenas um highlight temporário acionado por hover (`hover_in` / `hover_out`). Ao clicar em um card de referência no painel lateral ou em um POI correspondente no visualizador do mapa, a referência não é mantida selecionada de forma persistente: o destaque visual em ciano apenas pisca enquanto o cursor do mouse está sobre o elemento, desaparecendo assim que o usuário move o ponteiro. Isso prejudica a ergonomia e usabilidade do editor, forçando o usuário a repetidamente passar o mouse sobre os cards para inspecionar vínculos.

## What Changes

- **Seleção Persistente de Card de Referência**: Permite que o usuário clique em um `CardReferencia` no painel lateral para selecioná-lo de forma persistente. O card ativo recebe destaque visual (borda e fundo diferenciados) e seus POIs associados no mapa permanecem destacados em ciano mesmo após o mouse deixar a área do painel.
- **Fallback de Destaque no Desarmamento de Hover**: Ajusta a rotina de remoção de destaques (`remover_destaque_pois`) para restaurar a exibição da referência selecionada após previews efêmeros de hover em outros cards.
- **Alternância e Desseleção (Toggle/Deselect)**: Permite desmarcar a referência selecionada clicando novamente no card ativo ou clicando em área vazia do visualizador de mapas.
- **Seleção Bidirecional pelo Mapa**: Ao clicar com o botão esquerdo sobre um Ponto de Interesse (POI) no mapa em modo normal (fora do modo de linkagem), o sistema identifica se o POI pertence a alguma referência do mapa ativo, seleciona o card correspondente no painel direito e rola a lista para torná-lo visível.

## Capabilities

### Modified Capabilities
- `editor-mapas-referencias`: Adiciona requisitos e cenários para seleção persistente de referências no painel lateral, sincronização bidirecional entre cliques no mapa e no painel, e manutenção do destaque visual de POIs vinculados.

## Impact

- `editor/views/widget_painel_referencias.py`: Implementação de `mousePressEvent` em `CardReferencia`, estilização dinâmica do estado selecionado e controle do card selecionado ativo com emissão de sinais em `PainelReferencias`.
- `editor/views/widget_editor_mapas.py`: Rastreamento de `referencia_selecionada`, fallback em `remover_destaque_pois`, integração de seleção de referência a partir de cliques em POIs na cena gráfica e rolagem do painel.
- Testes unitários em `editor/views/widget_painel_referencias_test.py` e `editor/views/widget_editor_mapas_test.py`.
