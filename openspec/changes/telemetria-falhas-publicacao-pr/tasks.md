## 1. Testes de Integração e Contrato de Telemetria (TDD - Fase Vermelha)

- [ ] 1.1 Criar testes de integração em `editor/core/servico_submissao_test.py` verificando o contrato fim-a-fim entre falhas no `ServicoSubmissao` e o despacho correto para a função de telemetria com as tags e categorias esperadas (`git_proxy`, `github_api`, `git_local`, `autenticacao`, `rede`, `inesperado`).
- [ ] 1.2 Criar testes unitários em `editor/core/telemetria_test.py` para as funções `capturar_falha_submissao` e `registrar_breadcrumb_submissao`, validando níveis de severidade (`fatal`, `error`, `warning`), anexação de diário, formatação de tags, sanitização de caminhos e resiliência quando o Sentry estiver ausente.

## 2. Implementação da Biblioteca de Telemetria (TDD - Fase Verde)

- [ ] 2.1 Implementar a função `capturar_falha_submissao` em `editor/core/telemetria.py` suportando categorização taxonômica de erros, definição dinâmica de severidade no escopo Sentry, inclusão de contexto operacional sanitizado e anexo automático do diário de comandos.
- [ ] 2.2 Implementar a função `registrar_breadcrumb_submissao` em `editor/core/telemetria.py` para registro cronológico de eventos sob a categoria `submissao_pr`.

## 3. Instrumentação do `ServicoSubmissao` (TDD - Fase Verde)

- [ ] 3.1 Adicionar registro de breadcrumbs em `ServicoSubmissao.submeter_sugestao` a cada transição de progresso na função auxiliar `reportar(porcentagem, mensagem)`.
- [ ] 3.2 Instrumentar interceptação e captura de falhas em `fazer_push_proxy` (categoria `git_proxy`), `solicitar_abertura_pr` (categoria `github_api`), `criar_commit_sugestao` (categoria `git_local`), validação de autenticação (categoria `autenticacao`) e exceções gerais em `submeter_sugestao` (categoria `inesperado`).

## 4. Resiliência e Logging na Thread de Publicação (`worker.py`)

- [ ] 4.1 Criar testes em `editor/core/worker_test.py` validando o tratamento resiliente e o logging crítico na `TarefaPublicacao`.
- [ ] 4.2 Atualizar `TarefaPublicacao.run()` em `editor/core/worker.py` para substituir `traceback.print_exc()` por `logger.critical(..., exc_info=True)` e captura de segurança.

## 5. Validação, Cobertura de 100% e Refatoração (TDD - Refactor & Coverage)

- [ ] 5.1 Executar a suíte de testes com medição de cobertura (`pytest --cov=editor.core.telemetria --cov=editor.core.servico_submissao --cov=editor.core.worker`) e garantir 100% de cobertura de código nos módulos modificados.
- [ ] 5.2 Executar análise estática de tipos com `mypy` e validar conformidade estrita de nomenclatura em português.
