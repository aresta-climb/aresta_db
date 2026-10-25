## Why

Ao desenhar novas rotas no Editor de Mapas, é frequente que uma nova via compartilhe o trecho final ou o topo com uma via pré-existente (confluência de saída, variantes e extensões). Atualmente, o editor exige que o usuário redesenhe manualmente todos os nós sobrepostos da outra rota ou fatie manualmente as linhas e edite os `pontos_uids` nas referências, gerando atrito e risco de inconsistências topológicas. Esta mudança introduz um fluxo intuitivo e ágil de confluência guiada com popover contextual flutuante, pré-visualização dinâmica ("ghost preview") dos caminhos remanescentes e fatiamento topológico atômico com suporte a desfazer/refazer.

## What Changes

- **Detecção Topológica de Caminhos a Partir de Snap (`topologia_trajeto.py`)**: Biblioteca pura para analisar o grafo de traçados (`PontoDeInteresse.uid`) e referências (`Referencia.pontos_uids` e `alvo_uid`) do mapa a partir de uma coordenada de snap, descobrindo todas as continuações possíveis até topos ou ancoragens, com deduplicação automática quando múltiplas rotas compartilham exatamente a mesma sequência remanescente de segmentos.
- **Guarda de 1º Clique (Saída Compartilhada vs Confluência)**: O fluxo de confluência/término só é acionado quando a nova rota já possui pelo menos 1 ponto anterior (`len(pontos_nova_rota) >= 1`), preservando intacto o fluxo de saída compartilhada quando o primeiro clique ocorre na base de uma rota existente.
- **Popover Contextual de Confluência no Traçado**: Ao clicar com snap magnético em um nó intermediário, ponto de junção entre sublinhas ou curva de uma rota existente que possui continuidade adiante, o editor abre um menu flutuante ancorado no cursor listando as opções de continuação disponíveis (com a 1ª opção pré-selecionada para confirmação imediata via `Enter` ou `1`), além da opção de apenas adicionar o nó e continuar desenhando.
- **Ghost Preview Dinâmico em Tempo Real**: Ao abrir o popover ou navegar pelas opções (teclado `↑`/`↓` ou hover do mouse), a cena gráfica exibe instantaneamente uma pré-visualização translúcida em destaque (verde) do traçado remanescente que será herdado, com gerenciamento seguro de ciclo de vida Qt/C++ (`shiboken6.isValid`).
- **Confluência Direta em Nós de Topo Real**: Se o clique de snap (após o 1º ponto) ocorrer diretamente no último nó da última sublinha das referências que passam por ali (sem segmentos subsequentes), a confluência é concluída imediatamente sem abrir menu intermediário.
- **Cancelamento Seguro e Não-Destrutivo**: Ao pressionar `Esc` ou clicar fora do popover, o clique é cancelado e nenhum nó é inserido, protegendo contra toques acidentais.
- **Fatiamento Inteligente e Recomposição Atômica de Referências**:
  - Se o snap ocorrer em nó intermediário ou curva, fatia a linha interceptada em duas sublinhas com novos UIDs NanoID disjuntos e atualiza os `pontos_uids` de todas as referências existentes que a continham.
  - Se o snap ocorrer exatamente em uma junção existente entre duas sublinhas (`indice_no == 0` ou `indice_no == len - 1` com sublinha seguinte), reaproveita a junção existente sem re-fatiar.
  - Cria a referência da nova rota composta pelo UID da sua linha exclusiva inicial seguido pelos `pontos_uids` herdados até o topo escolhido, aplicando `desambiguar_topos`.
- **Operação Atômica no Histórico Undo/Redo**: Todas as mutações estruturais (linhas, nós, referências e desambiguação de topos) são encapsuladas em um único macro `QUndoCommand` na pilha de histórico.

## Capabilities

### New Capabilities
- `confluencia-rotas-mapas`: Define a interação, a detecção de caminhos a montante com deduplicação, a interface de popover com ghost preview e a recomposição relacional de traçados (`uid` / `pontos_uids` / `alvo_uid`) para término conjunto e confluência de rotas no editor de mapas.

### Modified Capabilities
<!-- Nenhuma especificação de capacidades existentes tem requisitos alterados. -->

## Impact

- `editor/core/topologia_trajeto.py`: Novas estruturas e funções puras (`OpcaoCaminhoConfluencia`, `descobrir_caminhos_confluencia`, `montar_coordenadas_caminho_remanescente`) operando sobre `uid`, `pontos_uids` e `alvo_uid`.
- `editor/controllers/mapas_controller.py`: Novo método `confluir_rota_em_tracado` orquestrando fatiamento condicional, transferência de `pontos_uids` e desambiguação de topos em macro de histórico.
- `editor/views/componentes/popover_confluencia_rota.py`: Novo widget flutuante de seleção de confluência com pré-seleção da 1ª opção, atalhos numéricos e emissão de sinais de preview.
- `editor/views/widget_editor_mapas.py`: Integração do evento de clique em snap (com guarda de 1º ponto), renderização segura do ghost preview temporário e invocação do popover contextual.
