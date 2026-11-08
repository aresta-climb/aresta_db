## MODIFIED Requirements

### Requirement: Substituição de Imagem no Editor de Mapas em Memória RAM
O sistema SHALL permitir a substituição da imagem de fundo de um mapa existente (tanto pelo Editor de Mapas quanto pelo Editor de Dados) através do wizard unificado de duas abas (`"Importar Nova Imagem"` com recorte e `"Imagens do Croqui"`), atualizando a imagem em memória RAM, sincronizando `largura_mapa` e `altura_mapa` e oferecendo reajuste proporcional opcional dos Pontos de Interesse (POIs) em um único `CmdMacro` reversível no histórico.

#### Scenario: Substituição de Imagem Bem-Sucedida com Undo/Redo
- **WHEN** o usuário aciona `"Substituir Imagem..."` em um mapa e confirma uma imagem com as mesmas dimensões ($W_{\text{novo}} = W_{\text{antigo}}$ e $H_{\text{novo}} = H_{\text{antigo}}$)
- **THEN** o sistema SHALL atualizar o buffer em memória RAM e o campo `caminho_imagem_mapa` via `CmdMacro` e recarregar a imagem de fundo na cena preservando as coordenadas originais dos POIs, permitindo desfazer e refazer a operação

#### Scenario: Substituição de Imagem com Mudança de Resolução e Reajuste Proporcional de POIs
- **WHEN** o usuário substitui a imagem de um mapa que possui POIs por uma imagem com nova resolução ($W_{\text{novo}} \times H_{\text{novo}} \neq W_{\text{antigo}} \times H_{\text{antigo}}$) mantendo marcada a opção de reajuste proporcional de POIs
- **THEN** o sistema SHALL atualizar a imagem em memória RAM, atualizar `largura_mapa` e `altura_mapa` e reescalar proporcionalmente todos os POIs do mapa em um único `CmdMacro` atômico

#### Scenario: Desfazer Substituição com Reajuste Proporcional de POIs
- **WHEN** o usuário aciona Desfazer (`Undo`) após substituir a imagem de um mapa com mudança de resolução e reajuste de POIs
- **THEN** o sistema SHALL restaurar em uma única operação os bytes e caminho da imagem anterior, as dimensões `largura_mapa` e `altura_mapa` originais e as coordenadas e dimensões exatas de todos os POIs

### Requirement: Diálogo Robusto de Adição de Mapas
O sistema SHALL fornecer um diálogo unificado para adição e substituição de mapas contendo duas abas (`"Importar Nova Imagem"` com seleção de arquivo, Drag & Drop, barra de recorte interativo *rubber-band crop*, painel de metadados ricos e pré-processamento WebP em RAM; e `"Imagens do Croqui"` com busca textual e grade de miniaturas do disco e da memória RAM), validação de nomes e opção de reajuste proporcional de POIs no modo de substituição.

#### Scenario: Seleção de Arquivo com Exibição de Metadados e Pré-processamento
- **WHEN** o usuário seleciona ou arrasta um arquivo de imagem na aba `"Importar Nova Imagem"` do diálogo de mapa
- **THEN** o sistema SHALL exibir a pré-visualização gráfica com suporte a seleção de área de recorte (`✂ Recortar Área Selecionada` e `↺ Reverter Imagem Original`), apresentar resolução ($W \times H$), tamanho e formato nos metadados e pré-processar os bytes para WebP

#### Scenario: Seleção de Imagem na Galeria do Croqui
- **WHEN** o usuário alterna para a aba `"Imagens do Croqui"`, filtra ou seleciona uma miniatura existente na pasta `imagens/` ou em `_imagens_em_memoria`
- **THEN** o sistema SHALL exibir os metadados da imagem selecionada e habilitar a confirmação sem exigir reimportação de arquivo externo

#### Scenario: Validação de Conflito de Nomes em Tempo Real
- **WHEN** o diálogo opera em modo de adição e o usuário digita um nome de arquivo que já existe no buffer de memória RAM (`_imagens_em_memoria`) ou na pasta `imagens/` do disco
- **THEN** o sistema SHALL exibir alerta indicando o conflito e desabilitar a confirmação
- **WHEN** o diálogo opera em modo de substituição com destino fixo (`caminho_destino_fixo`)
- **THEN** o sistema SHALL permitir a substituição sobre o caminho alvo sem bloquear por colisão consigo mesmo

## ADDED Requirements

### Requirement: Reajuste Proporcional Puro de Geometrias de POIs
O sistema SHALL fornecer na biblioteca pura `editor/core/geometrias_poi.py` a função `redimensionar_pois_proporcionalmente` capaz de reescalar as coordenadas e dimensões de todas as geometrias de `PontoDeInteresse` (`circulo`, `quadrado`, `retangulo`, `poligono` e `linha.conteudo.nos`) de $(W_{\text{antigo}}, H_{\text{antigo}})$ para $(W_{\text{novo}}, H_{\text{novo}})$.

#### Scenario: Reajuste proporcional de círculos, quadrados, retângulos, polígonos e linhas
- **WHEN** `redimensionar_pois_proporcionalmente` é invocada com uma lista de POIs e fatores de escala $s_x = W_{\text{novo}} / W_{\text{antigo}}$ e $s_y = H_{\text{novo}} / H_{\text{antigo}}$
- **THEN** a função SHALL retornar novas mensagens `PontoDeInteresse` com coordenadas `x` e `comprimento` multiplicados por $s_x$, coordenadas `y` e `largura` multiplicadas por $s_y$, `raio` e `lado` multiplicados pela média geométrica $\sqrt{s_x \cdot s_y}$ (com mínimo $1$), e todos os vértices de `poligono` e nós de `linha.conteudo.nos` reescalados por $(s_x, s_y)$
