## Context

Ver `proposal.md` - Why.
O editor já dispõe de cálculo de snap magnético (`calcular_snap`), fatiamento em nó (`fatiar_linha_em_no`), fatiamento em curva (`fatiar_linha_em_ponto_curva`), atualização de referências (`atualizar_referencias_apos_fatiamento` operando sobre `ref.pontos_uids`) e desambiguação de topos (`desambiguar_topos`) no módulo puro [`editor/core/topologia_trajeto.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/topologia_trajeto.py).
Após a Migração 0005, os POIs de linha são identificados por `uid` (NanoID de 14 caracteres) e as referências utilizam `pontos_uids` e `alvo_uid` (resolvido via [`IndiceUidsModel`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/models/indice_uids_model.py) ou busca no setor).
O controlador [`editor/controllers/mapas_controller.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/controllers/mapas_controller.py) orquestra mutações atômicas com `QUndoStack`, e [`editor/views/widget_editor_mapas.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/widget_editor_mapas.py) gerencia o ciclo interativo de `modo_nova_rota` com proteção de ponteiros C++ via `shiboken6.isValid` e `_remover_item_seguro`.

## Goals / Non-Goals

**Goals:**
- **Library-First (`topologia_trajeto.py`)**: Implementar a estrutura `OpcaoCaminhoConfluencia` e a função pura `descobrir_caminhos_confluencia` que, dado um `ResultadoSnap`, as linhas, as referências do mapa e um mapa opcional de nomes de escaladas (`uid -> nome`), descobre todas as continuações até os topos, deduplica caminhos fisicamente idênticos e distingue se o ponto é um topo final real ou um ponto intermediário/junção.
- **Componente Popover Contextual (`editor/views/componentes/popover_confluencia_rota.py`)**: Widget flutuante leve para exibir as opções de confluência com a 1ª opção pré-selecionada, atalhos numéricos (`1`, `2`...), navegação por setas/hover, opção explícita de "Apenas adicionar ponto e continuar desenhando" e cancelamento seguro com `Esc` ou clique externo.
- **Ghost Preview Dinâmico no Canvas**: Renderizar em tempo real um `QGraphicsPathItem` com spline Catmull-Rom translúcida em verde destacando o caminho da opção focada no popover, gerenciado com `shiboken6.isValid` e `_remover_item_seguro`.
- **Guarda de 1º Clique e Confluência Direta em Topo Real**: Não interceptar o primeiro clique da nova rota (`len(pontos_nova_rota) == 0`); e quando `len >= 1` e o snap ocorrer em um topo final real (último nó da última sublinha da referência), concluir a rota imediatamente sem abrir popover.
- **Transação Atômica no Controller (`confluir_rota_em_tracado`)**: Orquestrar fatiamento condicional (fatiando nós intermediários/curvas ou reaproveitando nós extremos de sublinhas já fatiadas), criação da linha exclusiva inicial, atualização de `pontos_uids` e `desambiguar_topos` sob um único macro de histórico.
- **Conformidade Estrita com `AGENTS.md`**: Espelhamento 1:1 de arquivos `_test.py`, 100% de cobertura comportamental pela API pública e zero mocks para código interno.

**Non-Goals:**
- Confluência reversa (desenhar no sentido descendente, do topo para a base). O sentido dos nós é sempre Início $\to$ Topo.
- Mutações que cruzem múltiplos mapas simultaneamente (o escopo da confluência é restrito ao mapa ativo).

## Decisions

### Decisão 1: Descoberta Topológica Pura com Deduplicação e Classificação de Junção (`topologia_trajeto.py`)
A função `descobrir_caminhos_confluencia` analisará o `ResultadoSnap` contra `linhas` e `referencias` e classificará os 4 casos geométricos:
1. **Nó intermediário (`0 < indice_no < len(nos) - 1`)**: Exige fatiamento da linha interceptada em `sub1` e `sub2`; o caminho herdado começa em `sub2` seguido pelas sublinhas posteriores da referência (`ref.pontos_uids[idx_linha + 1:]`).
2. **Ponto de curva (`TipoSnap.CURVA`)**: Exige fatiamento em curva em `sub1` e `sub2`; o caminho herdado começa em `sub2` seguido por `ref.pontos_uids[idx_linha + 1:]`.
3. **Nó inicial de sublinha (`indice_no == 0`) ou nó final de sublinha intermediária (`indice_no == len(nos) - 1` com sublinhas posteriores em `ref.pontos_uids`)**: **Não exige fatiamento** da linha existente! O caminho herdado é a própria sublinha a partir de `indice_no == 0` (ou a sublinha seguinte `ref.pontos_uids[idx_linha + 1:]`).
4. **Nó de topo final real (`indice_no == len(nos) - 1` na última sublinha da referência, sem nenhuma continuação adiante)**: Sinalizado como `eh_topo_final=True` quando não houver outros caminhos intermediários saindo daquele nó, permitindo término direto sem popover.

Se duas ou mais referências produzirem exatamente a mesma tupla de `uids_subsequentes` e coordenadas remanescentes a partir do ponto de encontro, elas são agrupadas em uma única `OpcaoCaminhoConfluencia` com os nomes concatenados (ex: `"Via 1 / Via 2"`).

### Decisão 2: Popover Flutuante com 1ª Opção Pré-Selecionada e Ghost Preview Imediato
Ao abrir o `PopoverConfluenciaRota` sobre um ponto intermediário, a opção `[1]` já inicia selecionada, disparando imediatamente o sinal `opcao_focada` para que o Ghost Preview acenda na rocha no exato instante do clique.
- *Rationale*: Se houver apenas um caminho (ou se o primeiro já for o desejado), o usuário visualiza o resultado instantaneamente e confirma com um único `Enter` ou tecla `1`.

### Decisão 3: Guarda do Primeiro Ponto (`len(pontos_nova_rota) >= 1`)
Quando `len(pontos_nova_rota) == 0`, clicar sobre um nó ou curva existente apenas adiciona o ponto inicial da nova rota sem invocar o fluxo de confluência.
- *Rationale*: Preserva a ergonomia de criar duas rotas que saem do mesmo ponto inicial na base da parede (`1, 2`) e bifurcam mais acima.

### Decisão 4: Cancelamento Seguro (Opção B)
Pressionar `Esc` ou clicar fora do `PopoverConfluenciaRota` fecha o menu e descarta o clique, mantendo `pontos_nova_rota` no estado anterior ao clique.
- *Rationale*: Protege contra cliques acidentais em paredes densas com muitas linhas próximas.

### Decisão 5: Mutações Exclusivamente via Macro `QUndoStack` (`mapas_controller.py`)
O método `confluir_rota_em_tracado` agrupa a criação da escalada (se nova), o fatiamento condicional da linha alvo, a atualização dos `pontos_uids` das referências existentes, a adição da linha exclusiva da nova rota, a criação da nova `Referencia` e a chamada a `desambiguar_topos` dentro de `iniciar_grupo_undo` / `finalizar_grupo_undo`.

## Risks / Trade-offs

- **[Risco: Ponteiros C++ órfãos do Ghost Preview ao recarregar a cena]** $\to$ *Mitigação*: Usar `_remover_item_seguro` e verificar `shiboken6.isValid(self.item_ghost_preview_temp)` em todas as atualizações e no fechamento do modo de desenho.
- **[Risco: Linha avulsa no mapa sem `Referencia` vinculada]** $\to$ *Mitigação*: Se a linha interceptada não estiver vinculada a nenhuma `Referencia` em `mapa.referencias`, `descobrir_caminhos_confluencia` ainda constrói uma opção de continuação percorrendo os nós restantes da própria linha até seu fim.
