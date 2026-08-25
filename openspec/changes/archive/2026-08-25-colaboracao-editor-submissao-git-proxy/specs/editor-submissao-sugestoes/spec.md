## ADDED Requirements

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
Após a conclusão bem-sucedida do push para o `git-proxy`, o sistema MUST invocar a Edge Function `create-pr` para abrir ou atualizar formalmente a Pull Request no GitHub.

#### Scenario: Abertura de Nova Pull Request
- **WHEN** o push da nova branch `sugestao-<id_croqui>-<uuid8>` for confirmado
- **THEN** o sistema MUST enviar requisição HTTP POST para `create-pr` contendo a branch, título e descrição, persistindo a URL da PR retornada em `croqui_experimental.yaml`

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
