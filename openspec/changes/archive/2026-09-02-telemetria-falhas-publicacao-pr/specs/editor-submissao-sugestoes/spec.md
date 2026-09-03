## ADDED Requirements

### Requirement: Telemetria de Falhas e Categorização no Sentry
O `ServicoSubmissao` MUST interceptar e reportar ao Sentry qualquer exceção ocorrida durante as etapas de publicação de sugestões (`submeter_sugestao`, `fazer_push_proxy`, `solicitar_abertura_pr`, `criar_commit_sugestao`), associando a categoria taxonômica do erro, o nível de severidade correspondente e o contexto operacional enriquecido antes de propagar a exceção `ErroSubmissao`.

#### Scenario: Falha de Comunicação ou Rejeição no Git Proxy
- **WHEN** ocorrer erro durante o push HTTP para a Edge Function `git-proxy` (ex: HTTP 500, recusa de conexão ou erro no streaming de packfile)
- **THEN** o sistema MUST reportar o erro ao Sentry com `categoria_erro="git_proxy"`, nível `fatal`, tag `etapa="push_proxy"` e detalhes da URL e resposta HTTP sanitizados.

#### Scenario: Falha na Edge Function create-pr ou GitHub API
- **WHEN** a requisição REST para a Edge Function `create-pr` retornar status diferente de 200 ou falhar na comunicação com a API do GitHub
- **THEN** o sistema MUST reportar o erro ao Sentry com `categoria_erro="github_api"`, nível `fatal`, tag `etapa="abertura_pr"` e payload de erro retornado pelo servidor.

#### Scenario: Falha em Operações Git Locais via pygit2
- **WHEN** ocorrer exceção interna no `pygit2` durante criação de branch, indexação de arquivos ou geração de commit assinado
- **THEN** o sistema MUST reportar o erro ao Sentry com `categoria_erro="git_local"`, nível `fatal`, tag `etapa="commit_local"` ou `etapa="preparacao_branch"`.

#### Scenario: Falha de Autenticação ou Expiração de Sessão JWT
- **WHEN** a renovação de tokens falhar devido a sessão revogada ou expirada
- **THEN** o sistema MUST reportar o erro ao Sentry com `categoria_erro="autenticacao"`, nível `error`, tag `etapa="verificacao_auth"`.

#### Scenario: Falha Inesperada Geral
- **WHEN** ocorrer qualquer exceção não categorizada previamente durante a submissão
- **THEN** o sistema MUST reportar o erro ao Sentry com `categoria_erro="inesperado"`, nível `fatal` e stacktrace completo.

### Requirement: Registro Cronológico de Breadcrumbs de Submissão
O `ServicoSubmissao` MUST registrar breadcrumbs estruturados no Sentry a cada transição de progresso no fluxo de publicação, permitindo a reconstrução determinística do caminho percorrido até o ponto de falha.

#### Scenario: Emissão de Breadcrumbs por Etapa Concluída
- **WHEN** o `ServicoSubmissao` avançar nas etapas de autenticação, preparação de branch, sincronização de arquivos, commit, push e abertura de PR
- **THEN** o sistema MUST registrar breadcrumbs sob a categoria `submissao_pr` contendo a porcentagem concluída, a descrição da etapa e metadados contextuais (nome da branch, id do croqui).

#### Scenario: Preservação de Rastreabilidade em Caso de Erro Intermediário
- **WHEN** uma falha ocorrer em uma etapa intermediária (ex: 80% no push)
- **THEN** o relatório de erro no Sentry MUST conter a sequência completa de breadcrumbs registrados até aquele instante.

### Requirement: Resiliência de Telemetria e Proteção de Privacidade
A telemetria de submissão MUST operar de forma silenciosa e resiliente, sem mascarar ou impedir o fluxo normal de apresentação de erros ao usuário em caso de indisponibilidade do Sentry SDK, e aplicando sanitização de privacidade.

#### Scenario: Execução em Ambiente sem Sentry SDK ou sem Conexão
- **WHEN** o módulo `sentry_sdk` não estiver disponível ou a chamada de telemetria falhar
- **THEN** a função de telemetria MUST capturar a falha silenciosamente e permitir que a exceção original `ErroSubmissao` seja emitida para tratamento na interface do usuário.

#### Scenario: Sanitização de Dados Sensíveis e Anexo de Diário
- **WHEN** o relatório de erro de submissão for enviado ao Sentry
- **THEN** o sistema MUST sanitizar caminhos absolutos locais, ocultar tokens de autenticação e anexar os binários anonimizados do diário de comandos recente quando disponíveis.
