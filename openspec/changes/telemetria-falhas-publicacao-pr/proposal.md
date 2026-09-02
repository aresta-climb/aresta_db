## Why

Atualmente, qualquer falha durante a publicação de uma proposta de mudança (Pull Request) no Aresta Editor — seja por instabilidade de rede, expiração de sessão JWT, rejeição no firewall do `git-proxy`, erros de manipulação Git via `pygit2` ou falhas na Edge Function `create-pr` — é tratada localmente em segundo plano (`QThread`), sem propagação para o gancho global de exceções. Como resultado, 100% dessas falhas passam invisíveis para a telemetria do Sentry, impedindo que a equipe de engenharia diagnostique proativamente quebras na experiência de colaboração dos autores de croquis.

Esta mudança introduz a captura ativa, categorizada e enriquecida de falhas de submissão no Sentry, tratando falhas de upload de propostas de mudança com a mesma seriedade e prioridade de crashes de aplicação, estritamente alinhada aos princípios de engenharia do repositório (Library-First, 100% de cobertura de testes, TDD obrigatório e tudo em português).

## What Changes

- **Captura Granular no `ServicoSubmissao`**: Interceptação e despacho automático de exceções para o Sentry antes de levantar `ErroSubmissao`, associando o erro à etapa exata da operação.
- **Categorização Taxonômica de Falhas**: Classificação estruturada das falhas (`categoria_erro`: `git_proxy`, `github_api`, `git_local`, `autenticacao`, `rede`, `inesperado`) e ajuste correspondente do nível de severidade no Sentry (`fatal`, `error`, `warning`).
- **Breadcrumbs de Progresso da Submissão**: Registro cronológico automático de cada etapa da submissão como breadcrumbs no Sentry (`autenticacao_verificada`, `branch_preparada`, `arquivos_sincronizados`, `commit_gerado`, `push_enviado`, `pr_solicitada`), permitindo diagnosticar exatamente o ponto de interrupção.
- **Enriquecimento de Contexto e Sanitização**: Anexo de metadados operacionais ao evento (identificador do croqui `id_croqui`, branch alvo, código de status HTTP e corpo de resposta do servidor sanitizados sem vazamento de dados privados ou caminhos locais de arquivos, e anexo do diário recente de comandos).
- **Tratamento Resiliente na `TarefaPublicacao`**: Garantia de logging estruturado (`logger.error` / `logger.critical` com `exc_info=True`) e emissão de telemetria de fallback caso ocorram erros fora do fluxo principal.
- **Adesão a PRINCIPIOS.md**: Todas as funções, variáveis e testes 100% em português brasileiro, desenvolvimento via TDD rigoroso (Red-Green-Refactor), testes de integração de contratos prioritários e 100% de cobertura de testes unitários.

## Capabilities

### New Capabilities

### Modified Capabilities
- `editor-submissao-sugestoes`: Inclusão de requisitos de telemetria de falhas, registro de breadcrumbs de etapas, categorização de erros e enriquecimento de contexto no Sentry durante o fluxo de publicação.

## Impact

- **Código Afetado**:
  - `editor/core/telemetria.py`: Nova função utilitária pura `capturar_falha_submissao` e `registrar_breadcrumb_submissao` com tags, severidade dinâmica, anexos de diário e sanitização de privacidade.
  - `editor/core/servico_submissao.py`: Emissão de breadcrumbs a cada etapa e disparo de telemetria em caso de falhas nas operações de Git local, autenticação, Git Proxy e Edge Function `create-pr`.
  - `editor/core/worker.py`: Logging crítico estruturado em `TarefaPublicacao` e tratamento seguro de exceções residuais.
- **Dependências e Testes**: Não adiciona dependências externas; utiliza `sentry_sdk` já configurado. Suíte completa de testes automatizados com TDD acompanhando cada arquivo modificado (`editor/core/telemetria_test.py`, `editor/core/servico_submissao_test.py` e `editor/core/worker_test.py`), assegurando 100% de cobertura de testes unitários.
