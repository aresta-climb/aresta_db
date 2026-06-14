## Why

Precisamos entender como o banco de dados atual utiliza os diferentes campos das mensagens Protobuf (`Croqui` e `Indice`). À medida que o schema evolui, é fundamental saber a taxa de adoção de cada campo na prática (especialmente comparando croquis rascunho com os publicados) para limpar campos não utilizados e priorizar a manutenção dos campos mais críticos.

## What Changes

- Criação de um script analítico na pasta `scripts` que coleta dados sobre o uso dos campos de Protobuf no banco de dados.
- Geração de arquivos `.dot` contendo um modelo do schema Protobuf com uso de tabelas (`record` labels) detalhando os campos e a taxa de uso.
- Geração de duas variantes para cada modelo (Croqui e Índice): uma completa (com todos os campos) e uma filtrada (exibindo apenas os campos e mensagens com uso maior que zero).
- Cálculos detalhados exibindo contagens "Absolutas" (baseadas no total de arquivos no banco) e "Relativas" (baseadas no número de arquivos que instanciaram especificamente a mensagem pai).
- Adição de visualizações de mapa de calor em células individuais para diferenciar as métricas ("Relativo Pub.", "Em Publicados", "Relativo Todos", "Em Todos").
- Renderização do grafo em arquivo `.svg` usando a biblioteca Python `graphviz`, adicionando-a como dependência no `requirements.txt`.
- Inserção de uma legenda explicativa (HTML table) diretamente no topo do gráfico usando a propriedade `label` do Graphviz.
- Refatoração do extrator estático de comentários Protobuf da UI (`ProtobufWidgetFactory`) para uma biblioteca compartilhada em `aresta_api.core.proto_comments`, permitindo que os SVGs exportem tooltips interativos contendo a documentação de cada mensagem e campo.

## Capabilities

### New Capabilities
- `visualizacao-uso-protobuf`: Geração de relatórios visuais da taxa de adoção e preenchimento dos campos Protobuf nas instâncias do banco de dados (Croquis e Índices).

### Modified Capabilities
- Nenhuma

## Impact

- **Código:** Adição de novo script em `scripts/`.
- **Dependências:** Adição do pacote `graphviz` ao `requirements.txt` do `aresta_api` ou da pasta raiz, exigindo que as instâncias rodando o script tenham o binário de sistema `dot` instalado.
- **Relatórios:** Geração de imagens na pasta `reports/`.
