## ADDED Requirements

### Requirement: Desambiguação Seletiva de Topos Sob Demanda Topológica
O sistema SHALL aplicar desambiguação automática de nós finais de rotas de escalada no Editor de Mapas exclusivamente sob demanda topológica real. Círculos identificadores de final (`FIM_TOP`) com letras sequenciais (`A`, `B`, `C`...) SHALL ser gerados apenas quando duas ou mais rotas convergirem no mesmo ponto final ou quando duas ou mais rotas compartilharem trecho/início e se bifurcarem para finais distintos. Rotas isoladas sem nenhuma junção ou separação com outras rotas SHALL permanecer com o nó final configurado como nó de passagem (`PASSAGEM`) sem rótulo textual.

#### Scenario: Criação de múltiplas rotas isoladas no mesmo mapa
- **WHEN** o usuário cria duas ou mais rotas no mesmo mapa que não compartilham nós, linhas, inícios ou finais entre si
- **THEN** o sistema SHALL configurar o nó inicial de cada rota com seu respectivo número sequencial e SHALL manter o nó final de todas essas rotas isoladas como `PASSAGEM` com rótulo vazio, sem adicionar círculos ou letras de topo.

#### Scenario: Convergência de rotas no mesmo topo
- **WHEN** duas ou mais rotas com inícios distintos terminam exatamente no mesmo ponto final de topo (distância $\le 5.0\text{px}$)
- **THEN** o sistema SHALL atribuir a esse nó final compartilhado o tipo `FIM_TOP` com uma letra identificadora única (ex: "A") e atualizar as referências vinculadas.

#### Scenario: Bifurcação de rotas a partir de início ou tronco compartilhado
- **WHEN** duas ou mais rotas compartilham o início ou um segmento de linha e se dividem para pontos finais distintos (distância $> 5.0\text{px}$)
- **THEN** o sistema SHALL atribuir a cada um dos pontos finais distintos o tipo `FIM_TOP` com letras sequenciais distintas (ex: "A" e "B").

#### Scenario: Restauração de rota isolada após exclusão ou reversão de variante
- **WHEN** uma rota que possuía variante com identificadores de topo volta a ser a única rota do seu tronco após exclusão ou reversão (Undo) da variante
- **THEN** o sistema SHALL remover a letra identificadora do seu nó final e reverter o tipo do nó para `PASSAGEM` com rótulo vazio.

---

### Requirement: Unicidade Estrita de Identificadores de POI e Rótulo Inicial de Rotas
O sistema SHALL garantir identificadores de POI estritamente únicos para cada novo traçado ou elemento inserido no mapa ativo e no setor, impedindo colisões de chaves e referências duplicadas. Ao criar uma nova rota, o sistema SHALL calcular o próximo número de início sequencial disponível e gerar um ID de linha único considerando prioritariamente os POIs do mapa ativo e os mapas do setor desembrulhado, garantindo reversão completa e remoção de todos os itens gráficos da cena no histórico (Undo/Redo).

#### Scenario: Adição sequencial de múltiplas rotas avulsas ou conectadas no mapa ativo
- **WHEN** o usuário adiciona sucessivas rotas em um mapa
- **THEN** cada rota criada SHALL receber um ID de POI único (ex: `linha_1`, `linha_2`, `linha_3`), nós de início com números sequenciais distintos e não colidentes, e referências que apontem exclusivamente para os IDs de seus respectivos segmentos.

#### Scenario: Resolução de setor envelopado em ArquivoSetor ou proxy
- **WHEN** o setor fornecido estiver envelopado em mensagem `ArquivoSetor` (com conteúdo aninhado em `conteudo.mapas`) ou através de proxies de leitura
- **THEN** o sistema SHALL desembrulhar o setor corretamente para localizar todos os IDs e rótulos já existentes em todos os mapas do setor.

#### Scenario: Seleção independente de rotas no editor
- **WHEN** o usuário clica sobre o traçado de uma rota ou seleciona seu card de referência na barra lateral
- **THEN** apenas os segmentos pertencentes àquela rota específica SHALL ser destacados visualmente, sem selecionar ou destacar rotas vizinhas.

---

### Requirement: Preservação de POIs Não-Linha e Reversibilidade Atômica no Undo/Redo
O sistema SHALL garantir que operações de atualização de nós (como desambiguação de topos) localizem os índices reais e absolutos no array `pontos_de_interesse` do mapa ativo, preservando intactos todos os demais pontos de interesse existentes (como círculos de início ou retângulos) e permitindo que o histórico (`QUndoStack`) reverta a adição de forma limpa.

#### Scenario: Adição de nova rota em mapa contendo círculos ou outros POIs pré-existentes
- **WHEN** o usuário adiciona uma nova rota em um mapa que já contém círculos ou retângulos intercalados antes da nova linha
- **THEN** o sistema SHALL preservar intactos todos os círculos e retângulos existentes sem sobrescrever nenhum item por descompasso de índices.

#### Scenario: Desfazer atômico de rota sem deixar traçados órfãos na tela
- **WHEN** o usuário aciona Desfazer (Undo) após adicionar uma nova rota
- **THEN** todos os elementos visuais daquela rota SHALL ser imediatamente removidos da cena gráfica (`QGraphicsScene`), sem deixar traçados órfãos visíveis e restaurando o estado original de todos os demais POIs do mapa.
