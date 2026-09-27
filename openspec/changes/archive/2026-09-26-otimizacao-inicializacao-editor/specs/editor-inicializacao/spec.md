## ADDED Requirements

### Requirement: Inicialização Imediata e Imports Sob Demanda
O Editor Aresta SHALL instanciar o `QApplication` e exibir a primeira interface gráfica imediatamente no ciclo de arranque, postergando a importação de submódulos pesados e não essenciais até o momento de sua real necessidade.

#### Scenario: Inicialização em Modo Local Direto
- **WHEN** o editor for iniciado com o caminho de um croqui via argumento de linha de comando
- **THEN** a aplicação SHALL inicializar o `QApplication`, importar estritamente os componentes necessários para a exibição local e apresentar a `JanelaPrincipal` sem importar a tela de login, clientes de autenticação em nuvem ou tarefas de sincronização remota Git.

#### Scenario: Exibição Rápida da Janela de Inicialização Padrão
- **WHEN** o editor for iniciado no fluxo de execução padrão
- **THEN** a aplicação SHALL criar o `QApplication` e exibir a janela de inicialização visual imediatamente
- **THEN** módulos pesados auxiliares SHALL ser importados sob demanda durante as etapas subsequentes do fluxo.
