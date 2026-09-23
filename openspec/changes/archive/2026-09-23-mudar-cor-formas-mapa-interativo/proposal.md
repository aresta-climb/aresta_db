## Why

Atualmente, rotas e linhas avulsas (`ItemTrajetoLinha`) no mapa interativo possuem um menu de contexto completo para mudança de cor com a paleta de alto contraste para rochas e seleção de cor customizada. Em contrapartida, as formas geométricas de áreas de interesse (círculos, retângulos, quadrados e polígonos) exibem cores estáticas hardcoded (verde e azul translúcido) e não oferecem opção de troca de cor em seu menu de contexto, mesmo que o modelo Protobuf (`croqui.proto`) já suporte o campo `cor` em `PontoDeInteresse`.

Esta alteração traz paridade de interface para todas as geometrias do mapa interativo, permitindo diferenciar setores, blocos e áreas de interesse por cores diretamente pelo menu de contexto (botão direito) ou diálogo de edição, com suporte completo a Undo/Redo e opção de restauração da cor padrão do sistema.

## What Changes

- **Submenu "Mudar Cor" para Formas Geométricas**: Disponibiliza o submenu de cores no clique direito de círculos, retângulos, quadrados e polígonos, contendo a opção "Padrão do Sistema", a paleta de cores de alto contraste (`PALETA_CORES_ROCHA`) e a opção "Personalizada...".
- **Helper Compartilhado de Menu de Cores**: Unifica a criação e montagem do submenu de cores entre linhas/rotas e formas geométricas, eliminando código duplicado.
- **Renderização Dinâmica de Cor nas Formas**: Atualiza `QPen` (borda de 2px sólida com a cor selecionada) e `QBrush` (preenchimento translúcido com alpha 60) em `ItemBoundingCirculo`, `ItemBoundingRetangulo`, `ItemBoundingQuadrado` e `ItemBoundingPoligono`.
- **Coloração das Alças de Vértice em Polígonos**: Atualiza dinamicamente a cor dos pontos de vértice (`AlcaVertice`) do polígono para acompanhar a cor da forma.
- **Suporte a Reset ("Padrão do Sistema")**: Permite remover a propriedade `cor` do elemento, restaurando as cores originais padrão (verde translúcido para círculos/retângulos e azul translúcido para polígonos).
- **Sincronização em `carregar_de_dict` e Undo/Redo**: Garante que alterações de cor sejam refletidas imediatamente na tela e que operações de desfazer/refazer (Ctrl+Z / Ctrl+Y) restaurem as cores na cena.
- **Correção no Menu de Contexto do Polígono**: Padroniza o `contextMenuEvent` do `ItemBoundingPoligono` para integrar com a infraestrutura de histórico (`registrar_movimento_final`), corrigindo a falta de Undo/Redo ao renomear ou alterar propriedades.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability criada do zero -->

### Modified Capabilities
- `editor-mapas`: Adiciona os requisitos e cenários de alteração de cor via menu de contexto para formas geométricas (`circulo`, `retangulo`, `quadrado`, `poligono`), opção de restauração de cor padrão do sistema e sincronização com histórico de comandos (Undo/Redo).

## Impact

- **Código Afetado**: `editor/views/widget_editor_mapas.py` e testes associados em `editor/views/widget_editor_mapas_test.py`.
- **Dependências / APIs**: Nenhuma nova dependência externa; utiliza Qt widgets (`QMenu`, `QColorDialog`, `QPen`, `QBrush`) e comandos `QUndoCommand` já existentes no projeto.
