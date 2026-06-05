## MODIFIED Requirements

### Requirement: Exibição da Árvore de Dados do Croqui
O sistema SHALL exibir uma visão em formato de árvore listando hierarquicamente apenas as sub-mensagens contidas no `croqui.proto` que forem anotadas com a message option `MensagemFormatoUi.SEPARADO` ou `MensagemFormatoUi.ONEOF_CONTEUDO`. Outros campos escalares ou mensagens que não correspondam a essas opções não devem aparecer na árvore.
Para campos repetidos (`repeated`) dessas mensagens, a árvore deve apresentar um nó agrupador ("expando"), que ao ser expandido exibe os elementos da lista sequencialmente.

#### Scenario: Carregamento Inicial da Árvore
- **WHEN** a página de Editor de Dados é aberta
- **THEN** o sistema SHALL renderizar um `QTreeView` contendo apenas as mensagens/sub-mensagens anotadas com `MensagemFormatoUi.SEPARADO` ou `MensagemFormatoUi.ONEOF_CONTEUDO`, com o `Croqui` como raiz invisível ou implícita.

#### Scenario: Campos Repetidos como Expandos
- **WHEN** uma mensagem possui um campo do tipo `repeated` que contém mensagens `SEPARADO` ou `ONEOF_CONTEUDO`
- **THEN** a árvore SHALL renderizar um nó agrupador intermediário (expando) para o campo repetido, e listar cada item da coleção logo abaixo dele.

#### Scenario: Seleção de uma Mensagem na Árvore
- **WHEN** o usuário seleciona um nó de mensagem na árvore (seja nó comum ou item de um campo repetido)
- **THEN** o sistema SHALL carregar a visão completa de formulário daquela mensagem específica na área direita.

