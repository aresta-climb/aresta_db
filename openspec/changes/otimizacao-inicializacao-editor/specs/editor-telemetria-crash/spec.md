## MODIFIED Requirements

### Requirement: Inicialização da Telemetria e Captura Global de Erros
O Editor Aresta SHALL prover a biblioteca `editor/core/telemetria.py` para inicializar o cliente Sentry de forma leve no ciclo de vida da aplicação (`editor/main.py`), desativando a detecção e ativação automática de integrações com bibliotecas de terceiros (`auto_enabling_integrations=False`), e capturar de forma global e silenciosa quaisquer exceções não tratadas disparadas na thread principal (`sys.excepthook`) e em threads secundárias (`threading.excepthook`).

#### Scenario: Exceção não tratada na interface gráfica
- **WHEN** uma exceção não tratada é disparada em um callback ou slot do PyQt6
- **THEN** o interceptador global captura a exceção, registra os detalhes no log local e submete o evento de erro ao Sentry com `sentry_sdk.flush()`.

#### Scenario: Exceção em thread de sincronização em segundo plano
- **WHEN** uma thread de background (worker) sofre uma falha fatal não capturada
- **THEN** o `threading.excepthook` intercepta o erro e submete o relatório de diagnóstico ao Sentry.

#### Scenario: Inicialização rápida sem auto-integrações externas
- **WHEN** a função de inicialização da telemetria for executada no arranque da aplicação
- **THEN** o cliente Sentry SHALL ser inicializado com `auto_enabling_integrations=False`
- **THEN** o tempo gasto na inicialização do Sentry não SHALL bloquear a inicialização ou renderização da interface gráfica.
