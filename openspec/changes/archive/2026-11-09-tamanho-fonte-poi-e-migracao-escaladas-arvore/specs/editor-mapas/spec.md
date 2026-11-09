# Spec Delta

## ADDED Requirements

### Requirement: Dimensionamento Automático e Manual do Texto Visível em Pontos de Interesse
O sistema SHALL suportar o campo opcional `tamanho_fonte` em `Mapa.PontoDeInteresse` para controlar o tamanho da fonte de `texto_visivel`. Quando `tamanho_fonte` estiver ausente ou for `0`, o editor SHALL calcular o tamanho da fonte proporcionalmente às dimensões da geometria (`circulo`, `retangulo`, `quadrado`) e atualizá-lo ao redimensionar o POI. O usuário SHALL poder definir ou redefinir `tamanho_fonte` pelo menu de contexto e pelo diálogo de edição com Undo/Redo.

#### Scenario: Escala automática do texto visível ao criar e redimensionar retângulo, círculo ou quadrado
- **WHEN** um Ponto de Interesse do tipo `retangulo`, `circulo` ou `quadrado` possui `texto_visivel` preenchido (ex: `"132"`), `tamanho_fonte` igual a `0` (automático) e o usuário redimensiona a forma segurando `Ctrl + arrastar`
- **THEN** o sistema SHALL recalcular o tamanho da fonte proporcionalmente às novas dimensões da forma, centralizar o texto dentro da área e registrar a alteração no histórico ao soltar o mouse.

#### Scenario: Definição manual de tamanho_fonte pelo menu de contexto ou diálogo de edição
- **WHEN** o usuário define um valor explícito de `tamanho_fonte` (ex: `18`) para um Ponto de Interesse através da ação `"Tamanho da Fonte..."` no menu de contexto ou pelo diálogo de edição do POI
- **THEN** o sistema SHALL aplicar exatamente o tamanho de fonte configurado ao `texto_visivel`, persistir o campo `tamanho_fonte` no modelo Protobuf via comando no histórico (`QUndoStack`) e manter esse tamanho fixo mesmo se a caixa geométrica for redimensionada.

#### Scenario: Restauração para tamanho de fonte automático
- **WHEN** o usuário define `tamanho_fonte` como `0` (Automático) no diálogo de edição ou menu de contexto de um Ponto de Interesse
- **THEN** o sistema SHALL remover a sobrescrita manual de `tamanho_fonte` no modelo Protobuf via comando no histórico e voltar a dimensionar a fonte automaticamente conforme a geometria do POI.

## MODIFIED Requirements

### Requirement: Reajuste Proporcional Puro de Geometrias de POIs
O sistema SHALL fornecer na biblioteca pura `editor/core/geometrias_poi.py` a função `redimensionar_pois_proporcionalmente` capaz de reescalar as coordenadas, dimensões e tamanhos de fonte (`tamanho_fonte`) de todas as geometrias de `PontoDeInteresse` (`circulo`, `quadrado`, `retangulo`, `poligono` e `linha.conteudo.nos`) de $(W_{\text{antigo}}, H_{\text{antigo}})$ para $(W_{\text{novo}}, H_{\text{novo}})$.

#### Scenario: Reajuste proporcional de círculos, quadrados, retângulos, polígonos e linhas
- **WHEN** `redimensionar_pois_proporcionalmente` é invocada com uma lista de POIs e fatores de escala $s_x = W_{\text{novo}} / W_{\text{antigo}}$ e $s_y = H_{\text{novo}} / H_{\text{antigo}}$
- **THEN** a função SHALL retornar novas mensagens `PontoDeInteresse` com coordenadas `x` e `comprimento` multiplicados por $s_x$, coordenadas `y` e `largura` multiplicadas por $s_y$, `raio`, `lado` e `tamanho_fonte` (quando $> 0$, tanto no POI quanto nos nós de linha) multiplicados pela média geométrica $\sqrt{s_x \cdot s_y}$ (com mínimo $1$), e todos os vértices de `poligono` e nós de `linha.conteudo.nos` reescalados por $(s_x, s_y)$
