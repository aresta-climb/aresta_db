# Tasks

## 1. Guardiões de Rede com Liberação para o Sentry

- [x] 1.1 Atualizar `tests/bloqueador_rede.py` e `tests/bloqueador_rede_test.py` (via TDD Red-Green-Refactor) para permitir resolução de DNS e conexão de sockets para hosts com sufixo `.sentry.io` (`*.ingest.us.sentry.io`), verificando que `uv run pytest tests/bloqueador_rede_test.py` passa com 100% de cobertura
- [x] 1.2 Atualizar `editor/caos/bloqueador_rede.py` e `editor/caos/bloqueador_rede_test.py` (via TDD Red-Green-Refactor) para permitir conexões de saída para hosts `.sentry.io` mantendo o bloqueio de demais endereços externos, verificando que `uv run pytest editor/caos/bloqueador_rede_test.py --cov=editor.caos.bloqueador_rede` passa com 100% de cobertura

## 2. Telemetria Contínua e Escopo Isolado para Campanhas de Caos

- [x] 2.1 Atualizar `editor/core/telemetria.py` e `editor/core/telemetria_test.py` (via TDD Red-Green-Refactor) para prover o gerenciador de sessão contínua do Sentry para campanhas de caos (`ativar_sessao_sentry_robo_caotico`), o isolamento de escopo por semente e para o `ddmin` (`escopo_isolado_semente_sentry` / `escopo_silencioso_ddmin_sentry`), e o anexo garantido do arquivo `.json` em `capturar_crash_robo_caotico`, verificando que `uv run pytest editor/core/telemetria_test.py` passa sem erros

## 3. Oráculos com Traceback Real e Motor de Campanha + CLI Local

- [x] 3.1 Atualizar `editor/caos/oraculos_caos.py` e `editor/caos/oraculos_caos_test.py` (via TDD Red-Green-Refactor) para que todas as falhas de oráculo (`excecao_nao_tratada`, `erro_registrado_log`, `assimetria_undo_redo`, `violacao_principio_viii`, `corrupcao_diario`, `objeto_cpp_deletado`) levantem/preservem uma exceção com `__traceback__` completo, verificando que `uv run pytest editor/caos/oraculos_caos_test.py --cov=editor.caos.oraculos_caos` passa com 100% de cobertura
- [x] 3.2 Atualizar `editor/caos/motor_robo_caotico.py`, `editor/caos/motor_robo_caotico_test.py`, `editor/caos/executar_campanha_cli.py`, `editor/caos/executar_campanha_cli_test.py` e `editor/caos/README.md` para manter o Sentry ativo do início ao fim da campanha, isolar o `ddmin` preservando os *breadcrumbs* e o diário da semente que falhou e anexar o `.json` ao evento enviado, verificando que `uv run pytest editor/caos/ --ignore=editor/caos/regressao_caminhos_test.py --cov=editor.caos --cov-report=term-missing` atinge 100% de cobertura e `uv run ruff check` / `uv run mypy` passam sem avisos
