## ADDED Requirements

### Requirement: Exibição colapsável para listas (Repeated Fields)
O sistema DEVE exibir cada item de um repeated field que armazene sub-mensagens como um bloco colapsável (acordeão), não os renderizando todos totalmente abertos de imediato.

#### Scenario: Visualização inicial de itens
- **WHEN** um formulário com uma lista de itens for carregado
- **THEN** todos os itens da lista são exibidos inicialmente colapsados (fechados), exibindo apenas os cabeçalhos

### Requirement: Instanciação Lazy (Sob demanda)
A renderização e alocação de memória dos subwidgets Qt dos campos internos de um item de lista DEVE ocorrer apenas quando o bloco do item for expandido.

#### Scenario: Expandir item pela primeira vez
- **WHEN** o usuário clica para expandir um item da lista
- **THEN** o sistema instanciará dinamicamente os subwidgets daquele item e exibirá o formulário interno, permitindo edição

### Requirement: Títulos heurísticos para os itens colapsados
O sistema DEVE tentar descobrir o nome do item para exibi-lo no cabeçalho do bloco, inspecionando seus campos em busca de identificadores conhecidos.

#### Scenario: Item contendo campo de identificação (nome/id)
- **WHEN** uma sub-mensagem na lista contém um campo chamado `id`, `nome` ou `titulo` preenchido
- **THEN** o sistema usa o valor desse campo junto ao índice para compor o rótulo no acordeão (ex: "▶ Item 1 - Id: 07")

#### Scenario: Item genérico sem campo descritivo
- **WHEN** a sub-mensagem não contém ou não tem preenchidos os campos heurísticos
- **THEN** o sistema exibe apenas o índice do item (ex: "▶ Item 2")
