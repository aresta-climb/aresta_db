# editor-submissao-sugestoes Specification

## Purpose
Especificação dos fluxos de colaboração e envio de propostas de mudança do Aresta Editor via Supabase Git Proxy e GitHub API.
## Requirements
### Requirement: Criação e Assinatura de Commit Local via pygit2
O `ServicoSubmissao` MUST criar branches locais temporárias a partir da `upstream/main` mais recente e gerar commits assinados com os metadados do autor autenticado (`SessaoUsuario`), contendo estritamente os arquivos modificados da pasta `database/<id_croqui>/`.

#### Scenario: Criação de Nova Branch com Nome Único
- **WHEN** o autor submeter uma nova sugestão para o croqui `<id_croqui>`
- **THEN** o sistema MUST criar uma branch no formato `sugestao-<id_croqui>-<uuid8>` a partir da referência `upstream/main`

#### Scenario: Commit Assinado com Nome e E-mail do Autor
- **WHEN** o commit for gerado pelo `pygit2`
- **THEN** a assinatura (`pygit2.Signature`) MUST conter o `nome_completo` e o `email` da `SessaoUsuario` ativa, com mensagem no formato `sugestao(<id_croqui>): <titulo>\n\n<descricao>\n\nSigned-off-by: <nome_completo> <<email>>`

#### Scenario: Restrição de Escopo de Arquivos Modificados
- **WHEN** os arquivos do croqui experimental forem sincronizados para o repositório base local
- **THEN** apenas arquivos localizados dentro de `database/<id_croqui>/` (YAMLs e imagens) MUST ser adicionados ao índice do Git

### Requirement: Push Autenticado para o Supabase Git Proxy
O `ServicoSubmissao` MUST enviar a branch local para a Edge Function `git-proxy` utilizando o protocolo Git Smart HTTP (v2) sobre HTTPS com as credenciais do JWT da sessão ativa.

#### Scenario: Envio de Packfile com JWT Válido
- **WHEN** o comando `push` for executado pelo `pygit2`
- **THEN** o callback de autenticação MUST fornecer o token JWT da sessão ativa para autorização na Edge Function `git-proxy`

#### Scenario: Renovação Silenciosa de Token JWT antes do Push
- **WHEN** o token JWT estiver expirado ou a submissão for iniciada
- **THEN** o sistema MUST tentar renovar silenciosamente o token via `ClienteAuthSupabase.renovar_sessao` antes de disparar o push

#### Scenario: Falha de Renovação de Sessão
- **WHEN** a renovação do token falhar (sessão revogada)
- **THEN** o sistema MUST alertar o usuário sobre a necessidade de reautenticação e orientar o salvamento seguro antes de reabrir o fluxo de login

### Requirement: Abertura e Atualização de Pull Request via Edge Function create-pr
Após a conclusão bem-sucedida do push para o `git-proxy`, o sistema MUST invocar a Edge Function `create-pr` para abrir ou atualizar formalmente a Pull Request no GitHub. Quando disponível, o token OAuth do usuário (`token_usuario_github`) MUST ser utilizado para conferir autoria direta ao usuário no GitHub, mantendo fallback automático para a credencial do bot GitHub App caso o token do usuário não esteja presente ou seja inválido.

#### Scenario: Abertura de Nova Pull Request com Token do Usuário
- **WHEN** o autor estiver autenticado via GitHub e possuir token de acesso com escopo `public_repo`
- **THEN** a Edge Function `create-pr` MUST utilizar o token do usuário para abrir a Pull Request no GitHub, resultando na autoria do usuário com selo do GitHub App (`@usuario via editor-aresta[bot]`)

#### Scenario: Abertura de Pull Request com Fallback para o Bot
- **WHEN** o autor estiver autenticado por e-mail ou o token OAuth do usuário for inválido/expirado
- **THEN** a Edge Function `create-pr` MUST criar a Pull Request utilizando as credenciais da instalação do GitHub App (`editor-aresta[bot]`)

#### Scenario: Atualização de Pull Request Existente
- **WHEN** o croqui experimental já possuir `pull_request_branch` aberta pelo mesmo autor
- **THEN** o sistema MUST reutilizar a mesma branch no push, dispensando a criação de nova PR e notificando o autor sobre a atualização

#### Scenario: Recuperação de PR Fechada ou Aceita (Merged)
- **WHEN** a PR anterior vinculada ao croqui estiver fechada ou mesclada no GitHub
- **THEN** o sistema MUST limpar os metadados antigos de `croqui_experimental.yaml` e criar uma nova branch de sugestão

### Requirement: Validações Pré-Envio e Resumo na Interface
O editor MUST validar a consistência técnica das alterações antes de disparar operações de rede e apresentar um resumo claro dos arquivos afetados no diálogo de publicação.

#### Scenario: Bloqueio de Envio com Erros de Compilação
- **WHEN** o croqui experimental contiver erros de compilação ou validação no `croqui.yaml`
- **THEN** o sistema MUST bloquear a abertura do diálogo de publicação e orientar a correção

#### Scenario: Detecção de Ausência de Modificações
- **WHEN** o estado do croqui experimental for idêntico à versão `upstream/main`
- **THEN** o sistema MUST informar que não há alterações a serem enviadas e encerrar o fluxo sem realizar push

#### Scenario: Resumo de Arquivos no Diálogo de Envio
- **WHEN** o diálogo de submissão for exibido
- **THEN** o diálogo MUST apresentar a contagem e a lista de arquivos a serem enviados (ex: `croqui.yaml` e imagens adicionadas/modificadas)

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


