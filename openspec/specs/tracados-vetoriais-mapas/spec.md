# tracados-vetoriais-mapas Specification

## Purpose
Define a especificação técnica e funcional para representação, interpolação, compilação, renderização e interação com traçados vetoriais de vias e boulders em mapas de escalada.
## Requirements
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

### Requirement: Interpolação Matemática Spline Centripetal Catmull-Rom
O sistema SHALL fornecer uma biblioteca autônoma (Library-First) em Python para calcular a Spline Centripetal Catmull-Rom ($\alpha = 0.5$) a partir de uma lista de pontos 2D, convertendo os segmentos em Curvas de Bézier Cúbicas exatas e formatando a saída como uma string de Path SVG padrão (`caminho_svg`).

#### Scenario: Interpolação de Linha com Múltiplos Nós
- **WHEN** a biblioteca recebe uma sequência de pelo menos 2 pontos $(x_i, y_i)$
- **THEN** a biblioteca SHALL gerar uma curva contínua que passa rigorosamente por todos os pontos intermediários, retornando os pontos de controle de Bézier e a string SVG compatível com motores gráficos.

#### Scenario: Tratamento de Pontos Coincidentes ou Insuficientes
- **WHEN** a biblioteca recebe nós com coordenadas idênticas consecutivas ou menos de 2 pontos
- **THEN** o sistema SHALL sanitizar os nós descartando duplicatas e retornar uma representação geométrica válida sem erros de divisão por zero.

### Requirement: Compilação de SVG Path no Pipeline de Build
O sistema SHALL integrar a conversão Catmull-Rom no pipeline de compilação do Aresta DB (`build.py` / `deploy_generated.py`), transformando os nós de `conteudo` em dados pré-computados em `compilado` nos artefatos `.binarypb` e `compilado.yaml`.

#### Scenario: Geração de Croqui Compilado com Traçados
- **WHEN** o comando de build ou deploy é executado sobre croquis contendo elementos do tipo `linha`
- **THEN** o compilador SHALL calcular o `caminho_svg` de cada linha, definir a `caixa_delimitadora` e salvar os binários sem exigir recálculo de spline no cliente móvel.

### Requirement: Composição de Trechos em Referências
O sistema SHALL permitir que uma `Referencia` de escalada componha múltiplos elementos de linha e pontos de interesse através do campo `ids`, permitindo que vias e variantes compartilhem segmentos de traçado comuns.

#### Scenario: Seleção de Via com Trecho Compartilhado e Saída Própria
- **WHEN** uma referência lista `ids: ["trecho_base_comum", "trecho_fim_variante"]`
- **THEN** o sistema SHALL associar todos os segmentos à mesma entidade de escalada para fins de destaque unificado e navegação.

### Requirement: Hit-Testing Estrito em Traçados Vetoriais
O sistema SHALL restringir a área clicável e de seleção de uma linha de traçado vetorial exclusivamente à vizinhança imediata do seu traçado geométrico (stroke com tolerância controlada), desconsiderando completamente o espaço interno côncavo delimitado pelos nós extremos da curva aberta.

#### Scenario: Clique diretamente sobre o traçado da curva
- **WHEN** o usuário clica com o mouse a uma distância menor ou igual à tolerância de clique (ex: até 7px do traçado da curva)
- **THEN** o sistema SHALL registrar a colisão com a linha de traçado correspondente e marcá-la como selecionada.

#### Scenario: Clique no espaço vazio entre os extremos de uma curva aberta
- **WHEN** o usuário clica com o mouse em uma área que fica no interior do polígono imaginário formado entre os extremos de uma curva côncava ou travessia, mas a uma distância maior que a tolerância do traçado
- **THEN** o sistema SHALL ignorar a colisão com essa curva, permitindo que cliques atinjam elementos posicionados nessa região (como nós, outras vias ou o fundo do mapa).

#### Scenario: Seleção de nó de outra via posicionado na área vazia da curva
- **WHEN** o usuário clica sobre um nó ou elemento de outra via posicionado no vão interno de uma curva de travessia
- **THEN** o sistema SHALL selecionar o nó ou elemento clicado, sem que a curva de travessia vizinha intercepte o clique.

### Requirement: Destaque Visual da Curva Selecionada
O sistema SHALL renderizar a seleção de uma linha de traçado vetorial através de um halo luminoso ou contorno de destaque de alto contraste ao longo do próprio spline da curva, sem exibir caixas delimitadoras retangulares tracejadas nativas ao redor do item.

#### Scenario: Exibição de destaque em linha selecionada
- **WHEN** uma linha de traçado vetorial está no estado selecionado
- **THEN** o sistema SHALL desenhar um contorno/halo suave de destaque acompanhando todo o traçado da curva e ocultar a caixa delimitadora retangular padrão do Qt.

#### Scenario: Deseleção de linha de traçado
- **WHEN** a linha de traçado perde a seleção
- **THEN** o sistema SHALL remover o halo de destaque e restaurar a renderização padrão de traço da linha.

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

### Requirement: Robustez Topológica em Fatiamento de Travessias
O sistema SHALL validar estritamente a existência de pelo menos dois nós intermediários distintos ao identificar uma travessia compartilhada em linha existente, garantindo que o índice de entrada seja estritamente menor que o índice de saída e que ambos pertençam ao intervalo intermediário da linha original.

#### Scenario: Rota com duplo clique sobre nó intermediário existente
- **WHEN** o usuário finaliza uma nova rota com duplo clique sobre o mesmo nó intermediário de uma linha existente gerando múltiplos pontos coincidentes
- **THEN** o sistema SHALL reconhecer que não há segmento intermediário percorrido com múltiplos nós distintos e NÃO DEVE disparar o fatiamento triplo com índices de entrada e saída idênticos.

#### Scenario: Rota com travessia compartilhando nós intermediários válidos
- **WHEN** uma nova rota conecta a uma linha existente em um nó intermediário A e sai em um nó intermediário B posterior (onde 0 < A < B < N - 1)
- **THEN** o sistema SHALL fatiar a linha em três sublinhas válidas, mantendo no mínimo dois nós em cada trecho resultante e associando o trecho compartilhado à nova rota.

### Requirement: Sanitização de Pontos Duplicados em Traçados
O sistema SHALL sanitizar a lista de pontos coletados durante a criação de novos traçados antes de submetê-la ao controlador de mapas, eliminando pontos consecutivos idênticos ou com separação menor que a tolerância de clique.

#### Scenario: Duplo clique ao concluir traçado de rota
- **WHEN** o usuário conclui o traçado de uma nova rota utilizando duplo clique no mouse
- **THEN** o sistema SHALL descartar o ponto redundante gerado no mesmo local pelo primeiro clique do evento duplo, gerando um traçado sem nós com distância zero.

### Requirement: Fallback Resiliente em Adição de Traçados com Topologia Complexa
O sistema SHALL incorporar tratamento de exceções na camada de controle durante a análise topológica de sobreposição, assegurando que eventuais falhas no fatiamento revertam graciosamente para a criação da linha como traçado independente sem interromper o fluxo do usuário ou emitir erros não tratados.

#### Scenario: Falha inesperada durante tentativa de fatiamento topológico
- **WHEN** a análise topológica encontra uma inconsistência nos índices ou geometria durante o cálculo de fatiamento
- **THEN** o sistema SHALL registrar aviso em log e adicionar o traçado da nova rota pelo fluxo padrão simples sem fatiar a linha existente, preservando o estado do croqui.

