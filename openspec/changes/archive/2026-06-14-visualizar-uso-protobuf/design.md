## Context

Conforme a evolução do banco de dados de croquis cresce, novos campos são adicionados ao Protobuf (`croqui.proto` e `indice.proto`). Torna-se essencial identificar quais campos estão sendo amplamente utilizados ("em produção") e quais caíram em desuso, a fim de direcionar refatorações, limpezas e novas features. Para isso, precisamos de um script analítico que exiba a taxa de uso de cada campo de maneira visual.

## Goals / Non-Goals

**Goals:**
- Prover um grafo (Graphviz SVG e DOT) da estrutura de mensagens Protobuf (`Croqui` e `Indice`) de todo o banco de dados de croquis.
- Calcular a contagem de adoção de cada campo sob duas óticas: "Absoluta" (em relação ao total do banco) e "Relativa" (em relação à quantidade de vezes que a mensagem pai foi criada).
- Diferenciar as contagens em croquis com `publicar_croqui=True` do cenário global (todos os croquis).
- Gerar versões duplas dos relatórios: "Completo" (com todos os campos) e "Usado" (filtrando campos com contagem zero para simplificar a visualização).
- Adicionar uma tabela de legenda informativa fixada no topo de todos os gráficos gerados.
- Aplicar escala de cor de calor (azul = pouco usado, vermelho = muito usado) nas células do grafo para fácil percepção visual.
- Seguir fielmente os `PRINCIPIOS.md` do repositório, em especial TDD e 100% test coverage.

**Non-Goals:**
- Não iremos modificar os croquis ou alterar a base de dados.
- Não iremos criar um sistema web de analytics; apenas a geração de SVGs estáticos.
- Não iremos remover campos do `.proto` neste passo, apenas visualizar.

## Decisions

- **TDD & Estrutura Library-First:** De acordo com o Princípio II e IV, a lógica de contagem e geração de .dot não será um script monolítico solto. Teremos uma biblioteca (`scripts/visualizar_uso_protobuf_lib.py`) contendo classes ou funções puras que recebem caminhos de arquivos e retornam estruturas de dados/strings DOT. Estas funções terão `100%` de cobertura de testes no arquivo companheiro `_test.py`. O script principal `scripts/visualizar_uso_protobuf.py` apenas fará as chamadas usando o `argparse`.
- **Graphviz como Dependência Python:** Usaremos o pacote python `graphviz` listado no `requirements.txt` da raiz para abstrair as chamadas ao binário `dot` e exportar os arquivos SVG. Exigiremos que o host possua o executável `dot` instalado no sistema.
- **Tabelas HTML-like no Graphviz:** Para permitir que uma mesma "caixa" de mensagem mostre o nome do campo e suas múltiplas contagens em colunas (com cores de fundo independentes), as mensagens serão representadas como tabelas `record` usando a sintaxe HTML nativa do Graphviz.

## Risks / Trade-offs

- **[Risk] Falta do binário `dot` no ambiente do usuário** → Mitigação: O script capturará a exceção de binário não encontrado, alertando o usuário sobre a necessidade da instalação, mas de qualquer forma sempre escreverá os arquivos brutos `.dot` para que o usuário possa renderizar onde quiser.
- **[Risk] Complexidade de Parse de Recursão em Protobufs Cíclicos** → Mitigação: Embora `Croqui` não possua ciclos profundos no momento, a lógica de reflexão pelo `DESCRIPTOR` tratará a detecção de estruturas para evitar loops infinitos ou garantirá uma profundidade razoável no parsing do schema.
