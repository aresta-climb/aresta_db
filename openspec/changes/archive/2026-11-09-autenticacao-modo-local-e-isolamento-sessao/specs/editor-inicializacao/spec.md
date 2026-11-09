# Spec Delta

## MODIFIED Requirements

### Requirement: Fluxo de Transição para Janela Principal
A aplicação MUST preservar o loop principal de eventos (`app.exec()`) ativo durante todas as transições entre a `TelaDeAbertura`, a `TelaDeCarregamento` e a `JanelaPrincipal`, fechando a janela anterior e exibindo a próxima sem disparar o encerramento automático do aplicativo por ausência temporária de janelas visíveis. O processo só MUST encerrar quando o usuário cancelar explicitamente a `TelaDeCarregamento` (sem logout em andamento) ou fechar todas as janelas principais abertas.

#### Scenario: Inicialização Concluída
- **WHEN** todas as etapas de inicialização (pastas, cofre, autenticação e sincronização Git) forem concluídas com sucesso no modo padrão (sem caminho de croqui local)
- **THEN** a `TelaDeAbertura` MUST ser fechada e a `TelaDeCarregamento` MUST ser exibida mantendo o loop principal de eventos ativo

#### Scenario: Inicialização Concluída no Modo Local Direto
- **WHEN** as etapas de inicialização do modo local (pastas, cofre e autenticação, sem sincronização Git do repositório base) forem concluídas com sucesso para um caminho de croqui local informado via linha de comando
- **THEN** a `TelaDeAbertura` MUST ser fechada e a `JanelaPrincipal` MUST ser instanciada diretamente com `LocalRepoWorkspace` e o `GerenciadorSessao` autenticado, mantendo o loop principal de eventos ativo

#### Scenario: Abertura de Croqui Oficial, Novo ou Existente a partir da Tela de Carregamento
- **WHEN** o usuário (ou agente via MCP) cria um novo croqui, importa um croqui oficial ou seleciona um croqui do histórico na `TelaDeCarregamento` e o diálogo é aceito
- **THEN** a `JanelaPrincipal` MUST ser instanciada com o croqui selecionado, exibida na tela e mantida viva no loop principal de eventos (`app.exec()`), sem que o fechamento intermediário da `TelaDeCarregamento` dispare `aboutToQuit` ou encerre a aplicação

#### Scenario: Retorno da Janela Principal para a Tela de Carregamento via Abrir Novo
- **WHEN** o usuário aciona a opção "Abrir Novo" na `JanelaPrincipal` para selecionar outro croqui
- **THEN** a `JanelaPrincipal` anterior MUST ser fechada e a `TelaDeCarregamento` MUST ser reaberta sem encerrar o loop principal de eventos da aplicação

### Requirement: Inicialização Imediata e Imports Sob Demanda
O Editor Aresta SHALL instanciar o `QApplication` e exibir a primeira interface gráfica imediatamente no ciclo de arranque, postergando a importação de submódulos pesados e não essenciais até o momento de sua real necessidade.

#### Scenario: Inicialização em Modo Local Direto
- **WHEN** o editor for iniciado com o caminho de um croqui via argumento de linha de comando
- **THEN** a aplicação SHALL validar o caminho do croqui local imediatamente e delegar ao `ControladorAplicativo` com `sincronizar_git=False`, executando apenas a verificação/autenticação de sessão antes de apresentar a `JanelaPrincipal` sem importar ou executar a sincronização remota Git do repositório base nem a `TelaDeCarregamento`

#### Scenario: Exibição Rápida da Janela de Inicialização Padrão
- **WHEN** o editor for iniciado no fluxo de execução padrão
- **THEN** a aplicação SHALL criar o `QApplication` e exibir a janela de inicialização visual imediatamente
- **THEN** módulos pesados auxiliares SHALL ser importados sob demanda durante as etapas subsequentes do fluxo.
