# tracados-vetoriais-mapas Specification

## Purpose
Define a especificação técnica e funcional para representação, interpolação, compilação, renderização e interação com traçados vetoriais de vias e boulders em mapas de escalada.
## Requirements
### Requirement: Suporte a Cores em Pontos de Interesse e Traçados
O sistema SHALL suportar a definição de uma cor customizada no formato hexadecimal (`#RRGGBB`) no campo `cor` de cada `PontoDeInteresse` / `ElementoVisual`, permitindo que traçados de linhas, polígonos, círculos e retângulos sejam visualizados e renderizados com cores distintas.

#### Scenario: Definição de Cor Hexadecimal em Linha de Trajeto
- **WHEN** um elemento de traçado é criado ou editado com o campo `cor: "#FF6D00"`
- **THEN** o sistema SHALL armazenar a string hexadecimal no modelo e renderizar o traçado na cena gráfica com a cor laranja correspondente.

#### Scenario: Fallback para Cor Padrão
- **WHEN** um elemento de traçado ou POI não possui o campo `cor` preenchido
- **THEN** o sistema SHALL utilizar a cor padrão do sistema (verde para POIs genéricos, laranja/ciano para linhas).

### Requirement: Modelo de Dados de Linha de Trajeto no Protobuf
O sistema SHALL suportar a representação estruturada de traçados de vias de escalada em mapas através da mensagem `LinhaTrajeto`, com suporte a estilos de traço (`TRACEJADO`, `SOLIDO`, `PONTILHADO`) e uma união (`oneof representacao`) entre o modo de edição semântica (`conteudo`) e o modo otimizado para renderização (`compilado`), com todos os identificadores em português brasileiro.

#### Scenario: Definição de Linha de Trajeto em Modo Conteúdo (Edição)
- **WHEN** um mapa contém um elemento visual do tipo `linha` com dados de edição
- **THEN** o sistema SHALL armazenar uma lista ordenada de `NoTrajeto` em `conteudo.nos`, onde cada nó possui coordenadas inteiras $(x, y)$, um tipo semântico (`PASSAGEM`, `CIRCULO_IDENTIFICADOR`, `INICIO_AGACHADO`, `PROTECAO_FIXA`, `PARADA_INTERMEDIARIA`, `TOP_PARADA`, `CRUX`) e um rótulo textual opcional (`rotulo`).

#### Scenario: Definição de Linha de Trajeto em Modo Compilado
- **WHEN** um mapa é processado pelo pipeline de compilação
- **THEN** o sistema SHALL preencher o campo `compilado` com o `caminho_svg` contendo a sequência de comandos Bézier (`M ... C ...`), a `caixa_delimitadora` e a lista de `marcadores` pré-posicionados.

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

