## MODIFIED Requirements

### Requirement: Criação e Assinatura de Commit Local via pygit2
O `ServicoSubmissao` MUST criar branches locais temporárias a partir da referência `origin/main` mais recente e gerar commits assinados com os metadados do autor autenticado (`SessaoUsuario`), contendo estritamente os arquivos modificados da pasta `database/<id_croqui>/`, garantindo o isolamento do índice do Git contra qualquer alteração prévia fora do escopo do croqui.

#### Scenario: Criação de Nova Branch com Nome Único
- **WHEN** o autor submeter uma nova sugestão para o croqui `<id_croqui>`
- **THEN** o sistema MUST criar uma branch no formato `edicao-<id_croqui>-<uuid8>` a partir da referência `origin/main`

#### Scenario: Commit Assinado com Nome e E-mail do Autor
- **WHEN** o commit for gerado pelo `pygit2`
- **THEN** a assinatura (`pygit2.Signature`) MUST conter o `nome_completo` e o `email` da `SessaoUsuario` ativa, com mensagem no formato `edicao(<id_croqui>): <titulo>\n\n<descricao>\n\nSigned-off-by: <nome_completo> <<email>>`

#### Scenario: Restrição de Escopo de Arquivos Modificados
- **WHEN** os arquivos do croqui experimental forem sincronizados para o repositório base local
- **THEN** apenas arquivos localizados dentro de `database/<id_croqui>/` (YAMLs, Markdowns e imagens) MUST ser adicionados ao índice do Git

#### Scenario: Isolamento Rígido do Índice contra Arquivos Sujos Fora de Escopo
- **WHEN** o método `criar_commit_sugestao` for chamado para empacotar as alterações locais
- **THEN** o sistema MUST redefinir o índice do repositório (`repo.index`) carregando a árvore limpa do `head_commit` (`read_tree`) antes de adicionar os arquivos do croqui, impedindo que modificações locais em arquivos fora de `database/<id_croqui>/` sejam incluídas no commit gerado

### Requirement: Push Autenticado para o Supabase Git Proxy
O `ServicoSubmissao` MUST enviar a branch local para a Edge Function `git-proxy` utilizando o protocolo Git Smart HTTP (v2) sobre HTTPS com as credenciais do JWT da sessão ativa e validar explicitamente o status de atualização da referência remota reportado pelo servidor Git.

#### Scenario: Envio de Packfile com JWT Válido
- **WHEN** o comando `push` for executado pelo `pygit2`
- **THEN** o callback de autenticação MUST fornecer o token JWT da sessão ativa para autorização na Edge Function `git-proxy`

#### Scenario: Rejeição de Atualização de Referência no Servidor Git (`push_update_reference`)
- **WHEN** o endpoint `git-receive-pack` responder com HTTP 200 mas reportar falha na criação ou atualização da referência remota (mensagem não nula no callback `push_update_reference`)
- **THEN** o `ServicoSubmissao` MUST capturar o motivo da rejeição, reportar a falha ao Sentry na etapa `push_proxy` com `categoria="git_proxy"` e lançar `ErroSubmissao` imediatamente, interrompendo o fluxo antes de invocar `solicitar_abertura_pr`

#### Scenario: Renovação Silenciosa de Token JWT antes do Push
- **WHEN** o token JWT estiver expirado ou a submissão for iniciada
- **THEN** o sistema MUST tentar renovar silenciosamente o token via `ClienteAuthSupabase.renovar_sessao` antes de disparar o push

#### Scenario: Falha de Renovação de Sessão
- **WHEN** a renovação do token falhar (sessão revogada)
- **THEN** o sistema MUST alertar o usuário sobre a necessidade de reautenticação e orientar o salvamento seguro antes de reabrir o fluxo de login

### Requirement: Validações Pré-Envio e Resumo na Interface
O editor MUST validar a consistência técnica das alterações antes de disparar operações de rede e apresentar um resumo claro dos arquivos afetados no diálogo de publicação.

#### Scenario: Bloqueio de Envio com Erros de Compilação
- **WHEN** o croqui experimental contiver erros de compilação ou validação no `croqui.yaml` e o usuário acionar o envio de proposta
- **THEN** o sistema MUST solicitar confirmação explícita do usuário para enviar a proposta com erros para revisão colaborativa; caso cancelado, o envio é bloqueado, mas caso confirmado, o fluxo prossegue

#### Scenario: Detecção de Ausência de Modificações
- **WHEN** o estado do croqui experimental for idêntico à versão `origin/main`
- **THEN** o sistema MUST informar que não há alterações a serem enviadas e encerrar o fluxo sem realizar push

#### Scenario: Resumo de Arquivos no Diálogo de Envio
- **WHEN** o diálogo de submissão for exibido
- **THEN** o diálogo MUST apresentar a contagem e a lista de arquivos a serem enviados (ex: `croqui.yaml` e imagens adicionadas/modificadas)
