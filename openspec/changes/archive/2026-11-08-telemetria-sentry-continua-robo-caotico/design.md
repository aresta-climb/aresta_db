# Design

## Context

Veja `proposal.md` para a motivação completa. Na implementação anterior, o cliente do Sentry permanecia desativado (`ARESTA_DESATIVAR_TELEMETRIA=1` no `conftest.py` e sem chamada a `inicializar_telemetria()` na CLI) enquanto o Robô Caótico executava os passos de cada semente na interface Qt. Ele só era ligado momentaneamente dentro de `capturar_crash_robo_caotico()` após o término da semente e após as ~10 execuções de busca binária do `EncolhedorCaminhoCrash` (`ddmin`). Isso causou três problemas observados na prática:
1. **Perda total de *breadcrumbs***: enquanto o Editor executava comandos (`registrar_breadcrumb_comando`) e emitia logs (`logger.info` / `logger.warning`), o `sentry_sdk` estava desligado (`NonRecordingClient`), descartando toda a trilha cronológica da sessão.
2. **Ausência de *stacktrace* em falhas de oráculo**: falhas como `assimetria_undo_redo`, `violacao_principio_viii`, `corrupcao_diario`, `objeto_cpp_deletado` e `erro_registrado_log` sem `exc_info` instanciavam `RuntimeError(...)` sem `raise`, resultando em `__traceback__ = None` e eventos sem *stacktrace* no Sentry.
3. **Vazamento/poluição por chamadas diretas ou replays do `ddmin`**: workers como `TarefaSalvamento` chamam `capturar_excecao()` e `logger.critical()` no meio do passo antes de o arquivo `.json` existir, e os replays do `ddmin` sobrescreviam `_diario_ativo` e o escopo global do Sentry.

## Goals / Non-Goals

**Goals:**
- Manter o Sentry SDK genuinamente inicializado e ativo do início ao fim de qualquer campanha do Robô Caótico (`reportar_sentry=True`), permitindo tráfego para `*.ingest.us.sentry.io` / `*.sentry.io` nos bloqueadores de rede.
- Preservar 100% dos *breadcrumbs* reais dos passos $1 \dots K$ da semente que falhou (incluindo comandos da `QUndoStack` e logs do `aresta_editor`) e o `_diario_ativo` daquela semente, isolando completamente as reexecuções do `ddmin`.
- Garantir que 100% das falhas (exceções em slots/threads, logs `ERROR`/`CRITICAL` e falhas dos 3 oráculos) possuam um objeto de exceção com `__traceback__` real e completo.
- Anexar sempre o arquivo `.json` (`crash_seed_<SEED>_<TIPO>.json`) e o contexto `receita_robo_caotico` ao evento enviado ao Sentry.

**Non-Goals:**
- Não ativar envio ao Sentry nos testes unitários convencionais do repositório (fora das campanhas do Robô Caótico).
- Não enviar múltiplos eventos repetidos para as tentativas intermediárias de poda do `ddmin`.

## Decisions

### 1. Liberação Seletiva do Host do Sentry nos Guardiões de Rede
- **Decisão**: Tanto `BloqueadorRedeCaos` (`editor/caos/bloqueador_rede.py`) quanto `tests/bloqueador_rede.py` passam a reconhecer sufixos `.sentry.io` (como `o4511980548849664.ingest.us.sentry.io`) como destinos permitidos, ao lado de `127.0.0.1`, `::1` e `localhost`.
- **Racional**: Permite que o transporte HTTP em segundo plano do `sentry_sdk` permaneça ativo durante toda a campanha de *fuzzing* sem precisar desligar o guardião de rede que protege contra acessos acidentais ao GitHub, Supabase ou Cloudflare.

### 2. Sentry Sempre Ativo na Campanha + Isolamento de Escopo por Semente e no `ddmin`
- **Decisão**:
  1. No início de `MotorRoboCaoticoQt.executar_campanha(..., reportar_sentry=True)`:
     - Chamamos um gerenciador de contexto `ativar_sessao_sentry_robo_caotico()` em `editor/core/telemetria.py` que mantém o Sentry inicializado durante **toda** a campanha (suspendendo `ARESTA_DESATIVAR_TELEMETRIA` enquanto a campanha roda e configurando `LoggingIntegration(level=logging.INFO, event_level=None)` para que todos os logs virem *breadcrumbs* sem disparar eventos órfãos antes do `.json` estar pronto).
     - Enquanto `ativar_sessao_sentry_robo_caotico()` está ativo, chamadas diretas do código de produção a `capturar_excecao()` / `capturar_falha_submissao()` (como na `TarefaSalvamento`) apenas notificam o oráculo/registram um breadcrumb em vez de enviar um evento prematuro sem o `.json`, deixando o envio consolidado (com `.json` anexado) para o final da semente.
  2. Em cada semente da campanha:
     - Abrimos `with sentry_sdk.isolation_scope() as escopo_semente:` (limpando *breadcrumbs* e anexos anteriores) antes de `motor.executar_sessao()`.
     - Durante `motor.executar_sessao()`, todos os comandos, logs e o `_diario_ativo` da semente são gravados diretamente em `escopo_semente`.
     - Se a semente falhar no Passo $K$:
       - Preservamos a referência do `_diario_ativo` da semente que falhou.
       - Executamos o `ddmin` (`encolhedor.encolher(receita_bruta)`) dentro de um escopo filho descartável (`with sentry_sdk.new_scope():` + pausa de breadcrumbs de histórico/diário durante replay de `ddmin`), garantindo que as ~10 reexecuções do `ddmin` **não adicionem nenhum breadcrumb** em `escopo_semente` e **não sobrescrevam** `_diario_ativo`!
       - Após o `ddmin` gerar e salvar `crash_seed_<SEED>_<TIPO>.json`, restauramos `_diario_ativo` da semente original e chamamos `capturar_crash_robo_caotico(...)` ainda dentro de `escopo_semente`, anexando `crash_seed_<SEED>_<TIPO>.json` + `diario_pendente.bin` / `diario_salvo.bin` e enviando a exceção real com todos os *breadcrumbs* intactos dos passos $1 \dots K$!

### 3. Geração Obrigatória de `__traceback__` Real nos Oráculos
- **Decisão**: Em `OraculosCaos` (`editor/caos/oraculos_caos.py`):
  - Em `registrar_excecao(exc_type, exc_value, exc_tb)`: se `exc_tb is not None` e `exc_value.__traceback__ is None`, vinculamos `exc_value = exc_value.with_traceback(exc_tb)`. Se `exc_tb is None` e `exc_value.__traceback__ is None`, fazemos `try: raise exc_value except BaseException as exc_com_tb: exc_value = exc_com_tb`.
  - Em `verificar_integridade_objetos_qt`, `auditar_passo_historico`, `verificar_integridade_diario` e `registrar_erro_log`: levantamos a exceção dentro de um bloco `try: raise AssertionError(msg) except AssertionError as exc:` e delegamos para `registrar_excecao(type(exc), exc, exc.__traceback__, oraculo=...)`. Assim, **100% das falhas** possuem `excecao_original` com `__traceback__` completo e real para o Sentry.

## Risks / Trade-offs

- **[Risco] `LoggingIntegration` padrão do Sentry envia `logger.critical` imediatamente sem o `.json` anexado** → **Mitigação**: Configurar `LoggingIntegration(level=logging.INFO, event_level=None)` em `inicializar_telemetria()` (ou silenciar envios diretos durante o passo do robô), pois os erros de log já são capturados por `_HandlerLogErroCaos` com seu `exc_info` completo e enviados com o `.json` anexado logo após o encolhimento.
- **[Risco] Replays do `ddmin` sujarem o `isolation_scope` da semente** → **Mitigação**: Como `sentry_sdk.add_breadcrumb()` escreve no `isolation_scope` ativo, envolver o `encolhedor.encolher(receita_bruta)` em `with sentry_sdk.isolation_scope():` cria um clone isolado descartável para o `ddmin`, deixando o `isolation_scope` da semente original 100% intacto com apenas os *breadcrumbs* dos passos $1 \dots K$.
