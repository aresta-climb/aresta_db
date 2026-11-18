# Spec Delta

## ADDED Requirements

### Requirement: Registro Obrigatório do Servidor MCP no Ciclo de Vida da Aplicação
O Editor Aresta MUST instanciar o servidor MCP e registrar integralmente todas as ferramentas MCP globais e de edição durante a abertura da `TelaDeCarregamento` e da `JanelaPrincipal` em qualquer execução da aplicação ou suíte de testes, permitindo suprimir exclusivamente a abertura de porta TCP de rede (`iniciar_rede_mcp=False`) em testes automatizados em memória.

#### Scenario: Registro integral de ferramentas MCP mesmo sem abertura de rede
- **WHEN** a aplicação ou uma suíte de testes (incluindo o Robô Caótico) inicializa o fluxo de `TelaDeCarregamento` ou `JanelaPrincipal` com `iniciar_rede_mcp=False`
- **THEN** o servidor MCP MUST ser instanciado e todas as ferramentas MCP (conhecimento, gestão de croquis/PDF, comandos, visão e curadoria de betas) MUST ser importadas e registradas em memória sem abrir socket TCP.

### Requirement: Modo de Autoverificação Ponta a Ponta Offline (--smoke-test)
O executável do Editor Aresta MUST suportar um modo de autoverificação automatizada acionado via linha de comando (`--smoke-test`) que percorre o fluxo completo de produção sem mocks internos e sem acesso à internet externa, validando login OTP, sincronização Git local, servidor MCP HTTP, abertura/criação de croqui na janela principal, particionamento de PDF, parser de busca web e compilação/salvamento.

#### Scenario: Execução bem-sucedida do smoke test no pacote compilado
- **WHEN** o binário empacotado do Editor Aresta é iniciado com `--smoke-test` apontando para um servidor HTTP local de autenticação e um repositório Git local em diretório temporário isolado
- **THEN** a aplicação MUST completar o login por código OTP na `TelaDeAbertura`, sincronizar o repositório Git, iniciar o servidor MCP HTTP na `TelaDeCarregamento`, abrir um croqui na `JanelaPrincipal`, particionar um arquivo PDF em imagens WebP, validar o carregamento do extrator HTML de betas, salvar/compilar o croqui e encerrar com código de saída `0`.

#### Scenario: Falha imediata em caso de dependência nativa ausente no smoke test
- **WHEN** o binário empacotado iniciado com `--smoke-test` encontra qualquer exceção não tratada, falha de importação ou erro de execução em alguma etapa
- **THEN** o processo MUST registrar o erro em `stderr` e encerrar imediatamente com código de saída diferente de zero sem travar em diálogos modais.

## MODIFIED Requirements

### Requirement: Tratamento de Falhas na Inicialização
A aplicação MUST informar ao usuário se ocorrer um erro crítico que impeça a abertura do editor (inclusive durante a transição da `TelaDeAbertura` para a `TelaDeCarregamento` ou `JanelaPrincipal`), encerrando limpo o processo e liberando a trava de instância única sem deixar processos invisíveis em segundo plano, e MUST continuar a inicialização em modo offline caso a falha de sincronização remota ocorra sobre uma base local já existente.

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
