# Spec Delta

## MODIFIED Requirements

### Requirement: Tratamento de Falhas na Inicialização
A aplicação MUST informar ao usuário se ocorrer um erro crítico que impeça a abertura do editor (inclusive durante a transição da `TelaDeAbertura` para a `TelaDeCarregamento` ou `JanelaPrincipal`), encerrando limpo o processo e liberando as travas locais de seleção ou de croqui sem deixar processos invisíveis em segundo plano, e MUST continuar a inicialização em modo offline caso a falha de sincronização remota ocorra sobre uma base local já existente.

#### Scenario: Erro de Rede ou Disco
- **WHEN** ocorrer uma falha irrecuperável durante a inicialização
- **THEN** a aplicação MUST ocultar a `TelaDeAbertura` e exibir uma caixa de mensagem de erro crítica
- **THEN** se o erro for 404 em repositório da organização, a mensagem MUST instruir sobre permissões no GitHub

#### Scenario: Falha Não Crítica de Sincronização com Base Existente
- **WHEN** ocorrer uma falha de conexão de rede durante a sincronização de dados remotos e a base local de croquis já existir no disco
- **THEN** a aplicação MUST registrar um aviso no log e emitir atualização de status na interface
- **THEN** a aplicação MUST prosseguir normalmente com a inicialização e abrir o editor utilizando os dados locais

#### Scenario: Exceção Crítica Após Fechamento da Tela de Abertura na Transição de Janelas
- **WHEN** ocorrer uma exceção inesperada durante a abertura da `TelaDeCarregamento`, registro do servidor MCP ou instanciação da `JanelaPrincipal` após o fechamento da `TelaDeAbertura`
- **THEN** a aplicação MUST capturar e registrar a exceção na telemetria, exibir uma caixa de mensagem crítica visível ao usuário (exceto em modo `--smoke-test` automatizado), encerrar os servidores locais e finalizar o loop de eventos para não manter um processo zumbi sem janelas.

## ADDED Requirements

### Requirement: Trava de Instância Escopada por Seleção e por Croqui
O Editor Aresta MUST substituir a trava global única por uma trava dedicada à tela de seleção (`ArestaEditorTelaSelecao`) e uma trava escopada por croqui (`ArestaEditorCroqui_<id_croqui>`), permitindo a execução simultânea de múltiplas instâncias independentes em croquis distintos.

#### Scenario: Abertura simultânea de croquis distintos via linha de comando
- **WHEN** uma primeira instância do editor está executando com o croqui `"A"` e o usuário executa um segundo processo informando o croqui `"B"` diferente de `"A"`
- **THEN** o segundo processo MUST validar o caminho de `"B"` antes da checagem de instância, adquirir a trava `ArestaEditorCroqui_B` e abrir normalmente uma segunda `JanelaPrincipal` independente

#### Scenario: Bloqueio e elevação ao tentar reabrir o mesmo croqui via linha de comando
- **WHEN** o croqui `"A"` já está aberto em uma janela ativa e o usuário executa outro processo informando o mesmo croqui `"A"`
- **THEN** o segundo processo MUST detectar a trava `ArestaEditorCroqui_A` responsiva, trazer especificamente a janela de `"A"` para o primeiro plano, informar ao usuário que o croqui já está aberto e encerrar com código `0`

#### Scenario: Bloqueio de tela de seleção duplicada e liberação após abertura de croqui
- **WHEN** uma instância está aguardando seleção na `TelaDeCarregamento` sem croqui aberto e outro processo é iniciado sem argumentos de croqui
- **THEN** o segundo processo MUST elevar a `TelaDeCarregamento` existente e encerrar; assim que o primeiro processo abrir um croqui na `JanelaPrincipal`, a trava de seleção MUST ser liberada para que novas instâncias possam abrir outra `TelaDeCarregamento`
