## Context

Ver `proposal.md` - Why.
Atualmente, o editor já dispõe de cálculo de snap magnético (`calcular_snap`), fatiamento em nó (`fatiar_linha_em_no`), fatiamento em curva (`fatiar_linha_em_ponto_curva`), atualização de referências (`atualizar_referencias_apos_fatiamento`) e desambiguação de topos (`desambiguar_topos`) no módulo puro [`editor/core/topologia_trajeto.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/topologia_trajeto.py).
O controlador [`editor/controllers/mapas_controller.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/controllers/mapas_controller.py) já orquestra mutações atômicas com `QUndoStack`. O widget de cena [`editor/views/widget_editor_mapas.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/widget_editor_mapas.py) gerencia o ciclo interativo de desenho de nova rota (`modo_nova_rota`).
Falta integrar a camada de descoberta topológica a montante com um componente visual de escolha (popover) e a renderização do traçado fantasma (ghost preview).

## Goals / Non-Goals

**Goals:**
- **Library-First (`topologia_trajeto.py`)**: Implementar a função pura `descobrir_caminhos_confluencia` que, dado um ponto de snap e o conjunto de linhas e referências do mapa, retorna uma estrutura com todos os caminhos disponíveis para a frente até os topos.
- **Componente Popover Contextual (`editor/views/componentes/popover_confluencia_rota.py`)**: Componente flutuante leve e estilizado para exibir as rotas/topos alcançáveis, com atalhos numéricos (`1`, `2`...), eventos de foco/hover e emissão de sinais para o preview.
- **Ghost Preview Dinâmico no Canvas**: Renderizar em tempo real um `QGraphicsPathItem` com traçado pontilhado verde translúcido e nós destacados refletindo a opção atualmente focada no popover.
- **Confluência Direta em Topo**: Conectar e concluir imediatamente quando o snap for no último nó de uma rota existente.
- **Cancelamento Seguro**: Tecla `Esc` ou clique fora fecha o popover sem adicionar nenhum nó e sem sujar o estado.
- **Transação Atômica no Controller**: Conectar o novo traçado, fatiar linhas existentes, atualizar referências antigas, criar a nova referência e aplicar desambiguação de topos sob um único macro de histórico.
- **100% Cobertura de Testes Unitários e Testes de Integração**: Seguir estritamente TDD em todas as camadas.

**Non-Goals:**
- Confluência reversa (desenhar no sentido descendente, do topo para a base). O sentido é sempre Início $\to$ Topo.
- Mutações que cruzem múltiplos mapas (o escopo da confluência é restrito ao mapa ativo).

## Decisions

### Decisão 1: Descoberta Topológica Pura e Desacoplada (Princípio II de AGENTS.md)
A descoberta de caminhos a montante a partir de um snap magnético residirá exclusivamente em `editor/core/topologia_trajeto.py`, recebendo estruturas de dados / protobuf e retornando dataclasses puras (`OpcaoCaminhoConfluencia`).
- *Alternativa rejeitada*: Implementar a busca dentro de métodos do widget Qt. Quebraria o Princípio II (Library-First) e dificultaria testes automatizados.

### Decisão 2: Popover Flutuante com Ghost Preview vs Apenas Modificadores de Teclado
A confluência será apresentada através de um mini-menu popover aberto ao clicar no snap intermediário, acompanhado de Ghost Preview ao navegar pelas opções.
- *Rationale*: Permite desambiguar quando duas ou mais rotas passam pelo mesmo ponto e depois se separam (ex: Topo A vs Topo B), além de tornar a funcionalidade 100% descobrível visualmente sem depender de memorização de atalhos arcanos.
- *Alternativa rejeitada*: Apenas `Shift + Clique`. Não resolveria a ambiguidade quando há múltiplos caminhos adiante.

### Decisão 3: Confluência Direta em Nós de Topo sem Popover
Se o snap ocorrer no nó final de uma rota existente, a nova rota se junta diretamente àquele nó e conclui o modo de desenho na hora.
- *Rationale*: No nó de topo não há caminhos remanescentes para escolher e não faz sentido "apenas adicionar nó e continuar desenhando" no mesmo ponto final. Reduz cliques desnecessários.

### Decisão 4: Cancelamento Seguro (Opção B)
Se o usuário der `Esc` ou clicar fora do popover, a ação é cancelada e o nó não é adicionado.
- *Rationale*: Evita que cliques imprecisos ou acidentais durante o traçado insiram nós indesejados sobre linhas existentes.

### Decisão 5: Mutações Exclusivamente via Comandos QUndoCommand (Princípio VII)
O método `confluir_rota_em_tracado` no `mapas_controller.py` agrupa o fatiamento da linha existente, criação da nova linha exclusiva, atualização das referências anteriores, criação da nova referência e desambiguação de topos em um macro atômico `iniciar_grupo_undo` / `finalizar_grupo_undo`.
- *Rationale*: Garante que `Ctrl+Z` reverta perfeitamente todo o estado visual e relacional em um único passo.

## Risks / Trade-offs

- **[Risco: Vias com múltiplos segmentos em cadeia `ids = [L1, L2, L3]`]** $\to$ *Mitigação*: A função `descobrir_caminhos_confluencia` percorre a lista de IDs da referência a partir da linha interceptada até o final, concatenando os nós de todas as sublinhas subsequentes para montar o traçado completo até o topo.
- **[Risco: Conflito de eventos de foco do Qt ao exibir popover durante modo de desenho]** $\to$ *Mitigação*: O popover será um `QWidget` popup sem captura modal exclusiva (ou com `Qt.WindowType.Popup`), direcionando teclas de atalho numéricas e navegação por setas para seus itens e repassando `Esc` para cancelamento limpo.
- **[Risco: Desambiguação de topo duplicar letras]** $\to$ *Mitigação*: Reutilização integral da função testada `desambiguar_topos`, que já garante letras sequenciais coerentes ou rótulos unificados para topos convergentes.
