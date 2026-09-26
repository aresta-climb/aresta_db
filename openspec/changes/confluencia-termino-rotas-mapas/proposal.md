## Why

Ao desenhar novas rotas no Editor de Mapas, é comum que uma nova via compartilhe o final ou o topo com uma via pré-existente (confluência de saída, variantes e extensões). Atualmente, o editor exige que o usuário redesenhe manualmente todos os nós sobrepostos da outra rota ou fatie manualmente as linhas e edite as listas de IDs nas referências, gerando fricção e risco de inconsistências topológicas. Esta mudança introduz um fluxo intuitivo e ágil de confluência guiada com popover contextual flutuante, pré-visualização dinâmica ("ghost preview") dos caminhos remanescentes e fatiamento topológico atômico com suporte a desfazer/refazer.

## What Changes

- **Detecção Topológica de Caminhos a Partir de Snap**: Biblioteca pura (`topologia_trajeto.py`) para analisar o grafo de traçados e referências do mapa a partir de uma coordenada de snap, descobrindo todas as continuações possíveis até topos ou ancoragens.
- **Popover Contextual de Confluência no Traçado**: Ao clicar com snap magnético em um nó intermediário ou curva de uma rota existente, o editor abre um menu flutuante ancorado no cursor listando as opções de continuação disponíveis até os topos correspondentes, além da opção de apenas adicionar o nó e continuar desenhando.
- **Ghost Preview Dinâmico em Tempo Real**: Ao navegar ou passar o mouse pelas opções do popover, a rocha exibe instantaneamente uma pré-visualização translúcida em destaque (verde) do traçado remanescente que será herdado.
- **Confluência Direta em Nós de Topo**: Se o clique de snap ocorrer diretamente no nó de topo/final de uma rota existente, a confluência é concluída imediatamente sem abrir menu desnecessário.
- **Cancelamento Seguro e Não-Destrutivo**: Ao pressionar `Esc` ou clicar fora do popover, o clique é cancelado e nenhum nó é inserido, protegendo contra toques acidentais.
- **Fatiamento e Recomposição Atômica de Referências**: Fatiamento automático da linha interceptada em duas sublinhas, atualização das referências das vias existentes para manter sua continuidade visual e geração da referência da nova rota composta pelo trecho inicial exclusivo e pelo trecho herdado.
- **Operação Atômica no Histórico Undo/Redo**: Todas as mutações estruturais (linhas, nós, referências e desambiguação de topos) são encapsuladas em um único macro `QUndoCommand`.

## Capabilities

### New Capabilities
- `confluencia-rotas-mapas`: Define a interação, a detecção de caminhos a montante, a interface de popover com ghost preview e a recomposição relacional de traçados para término conjunto e confluência de rotas no editor de mapas.

### Modified Capabilities
<!-- Nenhuma especificação de capacidades existentes tem requisitos alterados. -->

## Impact

- `editor/core/topologia_trajeto.py`: Novas funções puras para descoberta de caminhos de confluência a partir de nós/curvas e montagem da cadeia de IDs remanescentes.
- `editor/controllers/mapas_controller.py`: Novo método de orquestração atômica para confluir rotas com fatiamento, transferência de segmentos e desambiguação de topos em macro de histórico.
- `editor/views/widget_editor_mapas.py`: Integração do evento de clique em snap, renderização do ghost preview temporário e invocação do popover contextual.
- `editor/views/componentes/` ou `editor/views/dialogos/`: Novo widget leve/popover flutuante para seleção de confluência com atalhos de teclado e eventos de hover.
