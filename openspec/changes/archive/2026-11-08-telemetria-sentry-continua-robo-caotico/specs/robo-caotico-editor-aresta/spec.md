# Spec Delta

## MODIFIED Requirements

### Requirement: Oráculos de Exceção, Simetria de Undo/Redo e Integridade do Diário
A cada passo executado, o motor SHALL verificar três oráculos independentes: ausência de exceções não tratadas, logs de erro (`ERROR`/`CRITICAL`) ou objetos C++ deletados, simetria determinística do estado Protobuf na pilha de `Undo`/`Redo` e integridade estrutural do diário binário de sessão, garantindo que toda falha detectada possua um *traceback* real da pilha de execução no ponto da verificação.

#### Scenario: Detecção de exceção em slot Qt ou objeto C++ já deletado
- **WHEN** um slot Qt, temporizador ou thread em segundo plano lança uma exceção não tratada (como `RuntimeError: Internal C++ object already deleted`)
- **THEN** o oráculo de exceções SHALL capturar imediatamente a exceção original com seu *traceback* completo, interrompendo a semente atual e registrando a falha.

#### Scenario: Detecção de erro registrado no logger da aplicação
- **WHEN** um componente ou thread em segundo plano (como a tarefa de salvamento ou publicação) captura uma exceção internamente e emite um registro de nível `ERROR` ou `CRITICAL` no logger da aplicação
- **THEN** o oráculo SHALL interceptar o registro (extraindo `exc_info` quando presente ou levantando uma exceção real com *traceback* no ponto do log), interromper a semente atual e tratá-la como falha reproduzível para encolhimento e envio ao Sentry.

#### Scenario: Detecção de quebra de simetria na pilha de Undo/Redo
- **WHEN** o motor executa `Undo` ou `Redo` para um índice da pilha de histórico previamente visitado (sem salvamento modificador intermediário) e a serialização determinística do Protobuf diverge do hash registrado naquele índice
- **THEN** o oráculo de simetria SHALL levantar e capturar uma `AssertionError` com *traceback* completo da pilha de chamadas, reportando a falha de corrupção de estado ou mutação fora de comando de histórico.

#### Scenario: Verificação de integridade do diário transacional
- **WHEN** comandos são gravados no diário pendente ou consolidados no diário salvo durante a sessão
- **THEN** o oráculo de diário SHALL validar que os arquivos binários do diário permanecem legíveis e desserializáveis sem erro, levantando exceção com *traceback* completo caso detecte corrupção.

### Requirement: Bloqueio Hard de Rede Externa Durante os Testes
O sistema SHALL bloquear qualquer tentativa de conexão de rede externa ou abertura de navegador externo do sistema operacional durante a execução das sementes do robô caótico, exceto conexões de loopback (`127.0.0.1`, `::1`, `localhost`) e o endpoint de ingestão de telemetria do Sentry (`*.ingest.us.sentry.io` / `*.sentry.io`).

#### Scenario: Tentativa acidental de conexão externa durante um passo
- **WHEN** qualquer componente tenta abrir um socket TCP/UDP para um endereço externo não autorizado (ex: `8.8.8.8`, `github.com`, `supabase.co` ou `previa.arestaclimb.com`) durante a exploração
- **THEN** o guardião de rede SHALL impedir a conexão e lançar imediatamente `ErroAcessoRedeProibidoEmTeste`, fazendo o teste falhar com diagnóstico explícito.

#### Scenario: Permissão de tráfego de telemetria para o Sentry
- **WHEN** o SDK de telemetria resolve DNS ou abre conexão HTTPS para um host de ingestão do Sentry (`*.ingest.us.sentry.io` ou `*.sentry.io`) durante uma campanha de *fuzz testing*
- **THEN** o guardião de rede SHALL permitir a conexão sem lançar exceção de bloqueio.

### Requirement: Suíte de Regressão de Caminhos e Campanha por Tempo com Deduplicação
O sistema SHALL prover um teste de regressão que reexecute todos os arquivos JSON em `editor/caos/caminhos_regressao/`, um executor de campanha por orçamento de tempo que mantenha a telemetria ativa do início ao fim isolando os replays de poda (`ddmin`) para preservar os *breadcrumbs* da semente que falhou, e um ponto de entrada de linha de comando para execução local simplificada sem afetar a suíte unitária padrão.

#### Scenario: Execução automática de receitas de regressão salvas
- **WHEN** a suíte de testes automatizados é executada
- **THEN** todos os arquivos `.json` presentes em `editor/caos/caminhos_regressao/` SHALL ser carregados e reproduzidos sem falhas.

#### Scenario: Deduplicação de falhas idênticas durante campanha por tempo
- **WHEN** uma semente encontra uma assinatura de falha inédita durante uma campanha com envio ao Sentry ativo
- **THEN** o motor SHALL executar as reexecuções de busca binária (`ddmin`) em um escopo isolado e silencioso do Sentry (sem descartar nem sobrescrever os *breadcrumbs* e o diário acumulados nos passos da semente original), salvar o arquivo `.json` reduzido e despachar um único evento ao Sentry com os *breadcrumbs* originais, o *stacktrace* real e o `.json` anexado.

#### Scenario: Execução local via ponto de entrada de linha de comando
- **WHEN** o desenvolvedor executa o ponto de entrada de linha de comando do robô caótico sem argumentos adicionais
- **THEN** o sistema SHALL iniciar uma campanha local com janela visível por padrão, telemetria do Sentry habilitada e gravação automática de receitas `.json` em `editor/caos/caminhos_regressao/`, sem alterar o comportamento *headless* dos testes unitários do `pytest`.
