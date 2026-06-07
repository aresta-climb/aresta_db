## ADDED Requirements

### Requirement: O sistema de undo DEVE restaurar o foco global utilizando uma URI unificada
O sistema SHALL trocar a aba ativa globalmente e direcionar o foco de navegação interno da aba (seleção de nó da árvore ou arquivo da lista) conforme especificado na URI atrelada ao comando de undo/redo.

#### Scenario: Undo de comando da aba Dados altera foco global
- **WHEN** o usuário executa um Undo e a URI registrada era `page:dados/node:root/node:Croqui`
- **THEN** a `JanelaPrincipal` deve assegurar que a aba Dados seja ativada no `QStackedWidget` principal
- **THEN** o `WidgetEditorDados` deve selecionar o nó "Croqui" na árvore de navegação interna

#### Scenario: Undo de comando do Editor de Mapas
- **WHEN** o usuário executa um Undo de movimentação de ponto e a URI era `page:mapas/file:setor_principal.md`
- **THEN** a `JanelaPrincipal` muda a view global para Mapas
- **THEN** o arquivo `setor_principal.md` é selecionado no painel da esquerda do editor de mapas

### Requirement: Manipulação estruturada das URIs de contexto
O aplicativo SHALL centralizar a extração das partes da URI em uma classe (ex: `ContextoUIPath`), impedindo `replace` e `split` pulverizados no código fonte das views.

#### Scenario: Obtenção do prefixo e caminho local
- **WHEN** uma view recebe a string `page:dados/node:root/node:Croqui`
- **THEN** a view usa a classe de contexto para checar se a URI pertence a ela e para obter apenas a parte local (`node:root/node:Croqui`) pronta para consumo pelo componente de UI.
