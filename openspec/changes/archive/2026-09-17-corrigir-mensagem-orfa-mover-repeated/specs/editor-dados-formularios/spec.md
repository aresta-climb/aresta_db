## MODIFIED Requirements

### Requirement: Geração Dinâmica de Formulários
O sistema SHALL criar e exibir formulários na área de edição principal contendo TODOS os campos da mensagem selecionada atualmente na árvore (exceto os marcados como invisíveis), renderizando os controles de edição diretamente e sem a exibição de botões de Adicionar ou Remover no cabeçalho dos cards.
- **Cards de Campo**: Cada campo (primitivo ou sub-mensagem) SHALL ser renderizado dentro de um container do tipo Card (`QFrame` com borda fina e cantos arredondados) para demarcação visual clara.
- **Constrição de Largura**: Controles de edição primitivos curtos (números, strings curtas, combos, caixas de seleção) SHALL ter uma largura máxima configurada (ex: `150px` para números, `450px` para strings curtas) para evitar estiramento horizontal excessivo.
- **Ocultação de Campos Invisíveis**: Campos que possuam a opção de campo `formato_na_ui = INVISIVEL` no protobuf SHALL ser omitidos e não renderizados no formulário.
- **Regra Vazio = Ausente**: Campos de texto e markdown em branco SHALL ser automaticamente limpos no Protobuf (`ClearField`) e omitidos na serialização YAML; a inserção de dados SHALL restaurar sua presença.
- **Invalidação de Cache na Reordenação**: Ao reordenar itens, formulários em cache vinculados a instâncias anteriores desanexadas SHALL ser invalidados, assegurando que formulários reexibidos operem sobre a instância de mensagem ativa.

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

#### Scenario: Atualização e Invalidação de Formulário após Reordenação
- **WHEN** um elemento de coleção repetida é reordenado na árvore de dados
- **THEN** o sistema SHALL invalidar o formulário em cache associado à instância anterior do elemento
- **AND** renderizar/carregar o formulário vinculado à nova instância ativa do elemento, conectando seus controles de edição à mensagem correta do croqui.
