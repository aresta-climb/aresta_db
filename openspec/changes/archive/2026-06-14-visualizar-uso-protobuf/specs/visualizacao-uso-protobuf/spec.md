## ADDED Requirements

### Requirement: O sistema deve rastrear e calcular a adoção de todos os campos do Protobuf
O sistema SHALL analisar iterativamente cada arquivo `indice.binarypb` e os arquivos `compilado.binarypb` na pasta `generated/`, calculando a frequência absoluta e percentual com que cada campo de cada mensagem Protobuf foi preenchido.

#### Scenario: Geração de contagem para o Croqui
- **WHEN** o script de visualização é executado na pasta raiz
- **THEN** ele lê todos os croquis e acumula a taxa de preenchimento, separando "Croquis Publicados" de "Todos os Croquis"

### Requirement: O sistema deve exportar a visualização da arquitetura em formato Grafo
O sistema SHALL produzir a representação visual da estrutura do `Croqui` e do `Indice` usando a sintaxe `dot` do Graphviz, representando mensagens como tabelas e usando arestas para ligar campos de tipo Message para seus respectivos nós.

#### Scenario: Nós filhos e referências
- **WHEN** um campo (como `vias`) é do tipo mensagem (`Via`)
- **THEN** a tabela `Croqui` terá um ponteiro visual para o nó da tabela `Via`

### Requirement: O sistema deve colorir dinamicamente a taxa de adoção com escala de calor
O sistema SHALL aplicar uma cor de fundo (`bgcolor`) para as células de contagem no Graphviz variando de Azul (baixa porcentagem) a Vermelho (alta porcentagem), e Cinza para campos zerados.

#### Scenario: Visualização de uso zero
- **WHEN** o campo `url_video_beta` da `Via` nunca foi setado em nenhum croqui (0%)
- **THEN** a célula correspondente apresentará fundo cinza e texto opaco

### Requirement: O sistema deve seguir o rigor do TDD e Cobertura de Testes
A lógica central de geração SHALL estar desacoplada do parser de CLI e da interação com I/O bruto quando possível, implementada em uma biblioteca testável com 100% de cobertura no nível de testes unitários.

#### Scenario: Verificação de cobertura
- **WHEN** os testes unitários da nova rotina forem executados pelo pytest
- **THEN** a cobertura do arquivo `visualizar_uso_protobuf_lib.py` (ou nome equivalente) será de 100%
