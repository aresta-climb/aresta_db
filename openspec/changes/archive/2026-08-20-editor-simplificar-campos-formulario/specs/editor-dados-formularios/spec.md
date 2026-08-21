## MODIFIED Requirements

### Requirement: Geração Dinâmica de Formulários
O sistema SHALL criar e exibir formulários na área de edição principal contendo TODOS os campos da mensagem selecionada atualmente na árvore (exceto os marcados como invisíveis), renderizando os controles de edição diretamente e sem a exibição de botões de Adicionar ou Remover no cabeçalho dos cards.
- **Cards de Campo**: Cada campo (primitivo ou sub-mensagem) SHALL ser renderizado dentro de um container do tipo Card (`QFrame` com borda fina e cantos arredondados) para demarcação visual clara.
- **Constrição de Largura**: Controles de edição primitivos curtos (números, strings curtas, combos, caixas de seleção) SHALL ter uma largura máxima configurada (ex: `150px` para números, `450px` para strings curtas) para evitar estiramento horizontal excessivo.
- **Ocultação de Campos Invisíveis**: Campos que possuam a opção de campo `formato_na_ui = INVISIVEL` no protobuf SHALL ser omitidos e não renderizados no formulário.
- **Regra Vazio = Ausente**: Campos de texto e markdown em branco SHALL ser automaticamente limpos no Protobuf (`ClearField`) e omitidos na serialização YAML; a inserção de dados SHALL restaurar sua presença.

#### Scenario: Visualização de Campo Primitivo com Largura Constrita
- **WHEN** um campo primitivo (número ou string curta) é exibido no formulário
- **THEN** o controle de entrada correspondente SHALL respeitar o limite máximo de largura, não ocupando toda a extensão horizontal da tela.

#### Scenario: Ocultação de Campo com formato_na_ui Invisível
- **WHEN** o formulário é gerado para uma mensagem contendo campos anotados como `[(aresta.formato_na_ui) = INVISIVEL]`
- **THEN** o sistema SHALL pular a renderização desses campos, deixando-os ocultos ao usuário.

#### Scenario: Renderização Direta de Campos sem Botões de Presença
- **WHEN** o formulário é renderizado para uma mensagem do Protobuf
- **THEN** os controles de entrada de texto, números, booleanos e submensagens inline SHALL ser exibidos diretamente no card, sem exibir botões de "Adicionar" ou "Remover" no cabeçalho do campo.

#### Scenario: Esvaziamento de Campo de Texto
- **WHEN** o usuário apaga todo o texto de um campo de string ou markdown
- **THEN** o sistema SHALL remover o campo via `ClearField` no modelo do Protobuf e omiti-lo na serialização YAML.

## ADDED Requirements

### Requirement: Renderização de Booleanos Tri-State
O sistema SHALL renderizar campos booleanos como um `QComboBox` contendo 3 opções: Indefinido/Não informado (índice 0), Sim/Verdadeiro (índice 1) e Não/Falso (índice 2).
- **Customização**: O sistema SHALL extrair os rótulos de cada opção das opções do campo no Protobuf (`booleano_texto_indefinido`, `booleano_texto_sim`, `booleano_texto_nao`) ou usar textos padrão ("Não informado", "Sim", "Não").
- **Presença**: A seleção de "Não informado" SHALL executar `ClearField` no Protobuf, enquanto "Sim" define `True` e "Não" define `False`.

#### Scenario: Seleção de Opção Booleana Não Informado
- **WHEN** o usuário seleciona a opção "Não informado" em um campo booleano
- **THEN** o sistema SHALL limpar a presença do campo no Protobuf (`ClearField`).

#### Scenario: Seleção de Opção Booleana Sim ou Não
- **WHEN** o usuário seleciona "Sim" ou "Não" no dropdown booleano
- **THEN** o sistema SHALL atribuir respectivamente `True` ou `False` ao campo no Protobuf.

### Requirement: Renderização Especializada de Números e Coordenadas
O sistema SHALL renderizar números de ponto flutuante e coordenadas como `QLineEdit` com validação numérica, e inteiros como `QSpinBox` com suporte a estado nulo.
- **Ponto Flutuante**: O campo `QLineEdit` SHALL permitir entrada livre de casas decimais e manter o campo ausente quando vazio.
- **Inteiros**: O `QSpinBox` SHALL suportar um estado "Não definido" para campos ausentes e gravar explicitamente o valor quando definido como `0` ou superior.
- **Submensagens Inline de Coordenada**: O formulário SHALL exibir Latitude e Longitude; se ambos estiverem vazios, a submensagem de Coordenada SHALL ser limpa (`ClearField`).

#### Scenario: Edição de Coordenada GPS
- **WHEN** o usuário preenche a Latitude e Longitude de um campo de coordenada
- **THEN** o sistema SHALL instanciar e atualizar a submensagem `Coordenada` correspondente.

#### Scenario: Limpeza de Coordenada GPS
- **WHEN** o usuário apaga ambos os valores de Latitude e Longitude
- **THEN** o sistema SHALL executar `ClearField` da submensagem de coordenada pai.
