# Proposal

## Why

Atualmente, quando o Robô Caótico (*fuzz tester*) encontra uma falha durante suas campanhas, a telemetria do Sentry só é inicializada no instante final do envio pós-encolhimento (`ddmin`), fazendo com que todos os *breadcrumbs* gerados durante a execução dos passos da semente (comandos na `QUndoStack`, logs `INFO`/`WARNING` e atualizações do diário) sejam descartados e que falhas de oráculo sem `raise` cheguem ao Sentry sem *stacktrace*. Manter o Sentry genuinamente habilitado desde o início de qualquer execução de *fuzz testing* e anexar o arquivo `.json` da receita ao evento capturado garante relatórios completos no Sentry com *stacktrace* fiel, trilha cronológica de *breadcrumbs* intacta e reprodução determinística imediata.

## What Changes

- **Liberação de Tráfego para o Sentry nos Guardiões de Rede**: Atualizar `BloqueadorRedeCaos` (`editor/caos/bloqueador_rede.py`) e `tests/bloqueador_rede.py` para permitir conexões de saída estritamente para o endpoint de ingestão do Sentry (`*.ingest.us.sentry.io` / `*.sentry.io`), mantendo o bloqueio rigoroso para quaisquer outros hosts externos (`github.com`, `supabase.co`, `previa.arestaclimb.com`, `8.8.8.8`).
- **Sentry Continuamente Ativo Durante Todo o Fuzz Test**: Inicializar o Sentry SDK uma única vez no início das campanhas de *fuzz testing* (`MotorRoboCaoticoQt` / `executar_campanha_cli.py` / `robo_caotico_exploratorio_test.py`) e mantê-lo ativo durante toda a execução dos passos de cada semente, coletando nativamente *breadcrumbs* de comandos (`registrar_breadcrumb_comando`), logs (`LoggingIntegration`) e contexto do diário (`anexar_diario_escopo`).
- **Stacktrace Real para Todos os Oráculos e Logs de Erro**: Garantir em `OraculosCaos` (`editor/caos/oraculos_caos.py`) que todas as falhas detectadas (`excecao_nao_tratada`, `erro_registrado_log`, `assimetria_undo_redo`, `violacao_principio_viii`, `corrupcao_diario` e `objeto_cpp_deletado`) preservem ou levantem (`try: raise ... except ...`) uma exceção real com `__traceback__` completo no ponto da falha, além de interceptar chamadas diretas a `capturar_excecao` / `capturar_falha_submissao` durante os passos do robô.
- **Isolamento do `ddmin` e Anexo Garantido do `.json` no Escopo da Semente**: Executar cada semente em seu próprio escopo do Sentry e isolar as ~10 reexecuções de busca binária do `EncolhedorCaminhoCrash` (`ddmin`) em um escopo mudo separado (sem poluir os *breadcrumbs* da semente que falhou e sem disparar eventos intermediários sem anexo), anexando o arquivo `.json` (`crash_seed_<SEED>_<TIPO>.json`) e o contexto `receita_robo_caotico` ao escopo original do passo que falhou antes do despacho ao Sentry.
- **Ponto de Entrada Local Simplificado (`executar_campanha_cli.py`)**: Prover a CLI dedicada para execução local de *fuzz testing* com padrões prontos para uso (janela visível, Sentry ativo com anexo `.json` e gravação em `editor/caos/caminhos_regressao/`) sem afetar a suíte unitária *headless* do `pytest`.

## Capabilities

### New Capabilities

*(Nenhuma nova capability — estendemos as capabilities existentes de telemetria e do robô caótico).*

### Modified Capabilities

- `robo-caotico-editor-aresta`: Atualiza os requisitos de bloqueio de rede (permitindo o ingest do Sentry), de oráculos de falha (captura de erros de log `ERROR`/`CRITICAL` e geração obrigatória de `__traceback__` real) e de campanha/CLI local com isolamento de escopo durante o `ddmin`.
- `editor-telemetria-crash`: Atualiza o requisito de envio de falhas do Robô Caótico ao Sentry para exigir que o Sentry permaneça ativo durante toda a sessão de *fuzzing* (preservando os *breadcrumbs* reais dos passos e o *stacktrace* nativo) e anexe obrigatoriamente o arquivo `.json` da receita ao evento.

## Impact

- `editor/core/telemetria.py` e `editor/core/telemetria_test.py`
- `editor/caos/bloqueador_rede.py` e `editor/caos/bloqueador_rede_test.py`
- `tests/bloqueador_rede.py` e `tests/bloqueador_rede_test.py`
- `editor/caos/oraculos_caos.py` e `editor/caos/oraculos_caos_test.py`
- `editor/caos/receita_crash_robo.py` e `editor/caos/receita_crash_robo_test.py`
- `editor/caos/motor_robo_caotico.py` e `editor/caos/motor_robo_caotico_test.py`
- `editor/caos/robo_caotico_exploratorio_test.py`
- `editor/caos/executar_campanha_cli.py` e `editor/caos/executar_campanha_cli_test.py`
- `editor/caos/README.md`
