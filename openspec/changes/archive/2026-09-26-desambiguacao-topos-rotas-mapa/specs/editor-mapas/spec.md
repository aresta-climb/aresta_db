## ADDED Requirements

### Requirement: Desambiguação de Topos de Rotas Sob Demanda
O sistema SHALL aplicar desambiguação automática de nós finais de rotas de escalada no Editor de Mapas exclusivamente sob demanda topológica. Círculos identificadores de final (`FIM_TOP`) com letras sequenciais (`A`, `B`, `C`...) SHALL ser gerados apenas quando duas ou mais rotas convergirem no mesmo ponto final ou quando duas ou mais rotas compartilharem trecho/início e se bifurcarem para finais distintos. Rotas isoladas sem nenhuma junção ou separação com outras rotas SHALL permanecer com o nó final configurado como nó de passagem (`PASSAGEM`) sem rótulo textual.

#### Scenario: Criação de múltiplas rotas isoladas no mesmo mapa
- **WHEN** o usuário cria duas ou mais rotas no mesmo mapa que não compartilham nós, linhas, inícios ou finais entre si
- **THEN** o sistema SHALL configurar o nó inicial de cada rota com seu respectivo número sequencial e SHALL manter o nó final de todas essas rotas isoladas como `PASSAGEM` com rótulo vazio, sem adicionar letras de topo.

#### Scenario: Convergência de rotas no mesmo topo
- **WHEN** duas ou mais rotas com inícios distintos terminam exatamente no mesmo ponto final de topo
- **THEN** o sistema SHALL atribuir a esse nó final compartilhado o tipo `FIM_TOP` com uma letra identificadora única (ex: "A") e atualizar as referências vinculadas.

#### Scenario: Bifurcação de rotas a partir de início ou tronco compartilhado
- **WHEN** duas ou mais rotas compartilham o início ou um segmento de linha e se dividem para pontos finais distintos
- **THEN** o sistema SHALL atribuir a cada um dos pontos finais distintos o tipo `FIM_TOP` com letras sequenciais distintas (ex: "A" e "B").

#### Scenario: Restauração de rota isolada após exclusão ou reversão de variante
- **WHEN** uma rota que possuía variante com identificadores de topo volta a ser a única rota do seu tronco após exclusão ou reversão (Undo) da variante
- **THEN** o sistema SHALL remover a letra identificadora do seu nó final e reverter o tipo do nó para `PASSAGEM` com rótulo vazio.
