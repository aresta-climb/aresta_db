## ADDED Requirements

### Requirement: Navegação Direta, Scroll e Foco por Campo via ContextoUIPath
O sistema SHALL suportar o sufixo opcional `/campo:<nome_campo>` nas URIs de contexto (`ContextoUIPath`) destinadas à aba "Dados" para posicionar o formulário diretamente no campo alvo.
- **Extração no ContextoUIPath**: A classe `ContextoUIPath` SHALL extrair o identificador do campo em `campo_alvo` quando a URI contiver `/campo:<nome_campo>` e preservar `caminho_local_arvore` sem esse sufixo para resolução do nó na árvore.
- **Ativação Mesmo no Nó Já Selecionado**: Caso o nó indicado por `caminho_local_arvore` já esteja selecionado na árvore de dados no momento da requisição de foco, o editor de dados SHALL ainda assim executar o posicionamento e foco no `campo_alvo`.
- **Expansão Automática de Opções Avançadas**: Se o `campo_alvo` corresponder a um campo marcado com `(aresta.avancado) = true` no Protobuf e a seção "Opções Avançadas" estiver recolhida no formulário, o sistema SHALL expandir automaticamente a seção "Opções Avançadas" antes de realizar o scroll.
- **Scroll e Foco no Controle do Campo**: O formulário SHALL rolar seu `QScrollArea` até tornar o card ou container do `campo_alvo` visível na tela e transferir o foco para o controle de edição ou botão de ação principal daquele campo.

#### Scenario: Navegação direta para campo principal com scroll e foco
- **WHEN** o editor recebe uma requisição de foco com URI `page:dados/node:root/node:Croqui/expando:picos/item:0/campo:url_google_maps`
- **THEN** o sistema SHALL selecionar o Pico 0 na árvore da aba "Dados", rolar o formulário até o card do campo `url_google_maps` e focar no seu campo de texto.

#### Scenario: Navegação direta para campo recolhido em Opções Avançadas
- **WHEN** a seção "Opções Avançadas" está recolhida e o editor recebe uma requisição de foco para um campo avançado (ex: `page:dados/node:root/node:Croqui/campo:revisado_manualmente` ou `.../campo:trilhas`)
- **THEN** o sistema SHALL expandir automaticamente a seção "Opções Avançadas" do formulário, rolar até o card do campo solicitado e focar no seu controle.

#### Scenario: Requisição de foco para campo quando o nó já está selecionado na árvore
- **WHEN** o nó `node:root/node:Croqui/expando:picos/item:0` já está selecionado na árvore de dados e o usuário aciona uma ação no Painel apontando para `page:dados/node:root/node:Croqui/expando:picos/item:0/campo:localizacao`
- **THEN** o sistema SHALL rolar o formulário do pico já aberto até o campo `localizacao` e focar no seu controle de entrada.
