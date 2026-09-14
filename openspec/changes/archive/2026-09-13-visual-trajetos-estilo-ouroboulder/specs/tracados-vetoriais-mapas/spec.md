## MODIFIED Requirements

### Requirement: Suporte a Cores em Pontos de Interesse e Traçados
O sistema SHALL suportar a definição de uma cor customizada no formato hexadecimal (`#RRGGBB`) no campo `cor` de cada `PontoDeInteresse` / `ElementoVisual`, permitindo que traçados de linhas, polígonos, círculos e retângulos sejam visualizados e renderizados com cores distintas.

#### Scenario: Definição de Cor Hexadecimal em Linha de Trajeto
- **WHEN** um elemento de traçado é criado ou editado com o campo `cor: "#FFD600"`
- **THEN** o sistema SHALL armazenar a string hexadecimal no modelo e renderizar o traçado na cena gráfica com a cor amarela correspondente.

#### Scenario: Fallback para Cor Padrão
- **WHEN** um elemento de traçado de linha não possui o campo `cor` preenchido
- **THEN** o sistema SHALL utilizar o amarelo (`#FFD600`) como cor padrão de traçado de vias e boulders.

### Requirement: Modelo de Dados de Linha de Trajeto no Protobuf
O sistema SHALL suportar a representação estruturada de traçados de vias de escalada em mapas através da mensagem `LinhaTrajeto`, com suporte a estilos de traço (`TRACEJADO`, `SOLIDO`, `PONTILHADO`) e uma união (`oneof representacao`) entre o modo de edição semântica (`conteudo`) e o modo otimizado para renderização (`compilado`), com todos os identificadores em português brasileiro.

#### Scenario: Definição de Linha de Trajeto em Modo Conteúdo (Edição)
- **WHEN** um mapa contém um elemento visual do tipo `linha` com dados de edição
- **THEN** o sistema SHALL armazenar uma lista ordenada de `NoTrajeto` em `conteudo.nos`, onde cada nó possui coordenadas inteiras $(x, y)$, um tipo semântico (`PASSAGEM`, `CIRCULO_IDENTIFICADOR`, `INICIO_AGACHADO`, `PROTECAO_FIXA`, `PARADA_INTERMEDIARIA`, `TOP_PARADA`, `CRUX`, `PROTECAO_MOVEL`, `PROTECAO_PITON`, `PROTECAO_FITA`, `BURACO_CLIFF`, `FIM_TOP`, `SETA_DIRECIONAL`) e um rótulo textual opcional (`rotulo`).

#### Scenario: Definição de Linha de Trajeto em Modo Compilado
- **WHEN** um mapa é processado pelo pipeline de compilação
- **THEN** o sistema SHALL preencher o campo `compilado` com o `caminho_svg` contendo a sequência de comandos Bézier (`M ... C ...`), a `caixa_delimitadora` e a lista de `marcadores` pré-posicionados com seus respectivos tipos e ângulos tangentes calculados.

## ADDED Requirements

### Requirement: Renderização de Marcadores e Badges no Padrão Ouroboulder
O sistema SHALL renderizar círculos identificadores (`CIRCULO_IDENTIFICADOR`, `INICIO_AGACHADO`, `FIM_TOP`) sem bordas brancas espessas, utilizando um contorno escuro fino (1.0px a 1.5px), fundo preto neutro quando inativo, fundo na cor de destaque da via quando selecionado, e tipografia interna em negrito preenchendo entre 75% e 80% do diâmetro útil do círculo, garantindo consistência visual idêntica entre o Editor e o Aplicativo Móvel.

#### Scenario: Renderização de Círculo Identificador em Estado de Repouso
- **WHEN** o traçado da via ou o mapa é exibido sem que a via em questão esteja selecionada
- **THEN** o sistema SHALL desenhar o círculo identificador com fundo preto neutro (`#1A1A1A`), contorno sutil escuro, e o rótulo alfanumérico em branco centralizado e ampliado, sem qualquer borda branca interna espessa.

#### Scenario: Renderização de Círculo Identificador em Estado Ativo (Selecionado)
- **WHEN** o traçado da via ou a referência correspondente é selecionada pelo usuário (via clique, toque ou navegação no rodapé)
- **THEN** o sistema SHALL desenhar o círculo identificador com preenchimento na cor de destaque da via (amarelo ou cor configurada), contorno escuro fino, rótulo em branco centralizado e halo suave de seleção.

### Requirement: Renderização de Nó com Seta Direcional
O sistema SHALL suportar a exibição e compilação de nós do tipo `SETA_DIRECIONAL`, renderizando uma ponta de seta orientada pela tangente do spline da curva no ponto correspondente, indicando a direção de movimento, lance dinâmico ou progressão da via.

#### Scenario: Exibição de Seta Direcional ao Longo da Linha
- **WHEN** um traçado contém um nó do tipo `SETA_DIRECIONAL`
- **THEN** o sistema SHALL renderizar uma ponta de seta orientada na direção do fluxo da linha com a cor da via e contorno de contraste escuro.

#### Scenario: Compilação de Ângulo Tangente para Seta Direcional
- **WHEN** o pipeline de compilação processa um nó `SETA_DIRECIONAL`
- **THEN** o sistema SHALL calcular o ângulo da tangente da Spline Catmull-Rom naquele índice e gravar `angulo_graus_x100` no `MarcadorCompilado`.
