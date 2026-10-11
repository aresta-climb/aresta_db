# Spec Delta: editor-submissao-sugestoes

## MODIFIED Requirements

### Requirement: Criação e Assinatura de Commit Local via pygit2
O `ServicoSubmissao` MUST criar branches locais temporárias a partir da `upstream/main` mais recente e gerar commits assinados com os metadados do autor autenticado (`SessaoUsuario`), contendo estritamente os arquivos modificados da pasta `database/<id_croqui>/`, garantindo o isolamento do índice do Git contra qualquer alteração prévia fora do escopo do croqui.

#### Scenario: Criação de Nova Branch com Nome Único
- **WHEN** o autor submeter uma nova sugestão para o croqui `<id_croqui>`
- **THEN** o sistema MUST criar uma branch no formato `sugestao-<id_croqui>-<uuid8>` a partir da referência `upstream/main`

#### Scenario: Commit Assinado com Nome e E-mail do Autor
- **WHEN** o commit for gerado pelo `pygit2`
- **THEN** a assinatura (`pygit2.Signature`) MUST conter o `nome_completo` e o `email` da `SessaoUsuario` ativa, com mensagem no formato `sugestao(<id_croqui>): <titulo>\n\n<descricao>\n\nSigned-off-by: <nome_completo> <<email>>`

#### Scenario: Restrição de Escopo de Arquivos Modificados
- **WHEN** os arquivos do croqui experimental forem sincronizados para o repositório base local
- **THEN** apenas arquivos localizados dentro de `database/<id_croqui>/` (YAMLs e imagens) MUST ser adicionados ao índice do Git

#### Scenario: Isolamento Rígido do Índice contra Arquivos Sujos Fora de Escopo
- **WHEN** o método `criar_commit_sugestao` for chamado para empacotar as alterações locais
- **THEN** o sistema MUST redefinir o índice do repositório (`repo.index`) carregando a árvore limpa do `head_commit` (`read_tree`) antes de adicionar os arquivos do croqui, impedindo que modificações locais em arquivos fora de `database/<id_croqui>/` sejam incluídas no commit gerado

### Requirement: Abertura e Atualização de Pull Request via Edge Function create-pr
Após a conclusão bem-sucedida do push para o `git-proxy`, o sistema MUST invocar a Edge Function `create-pr` para abrir ou atualizar formalmente a Pull Request no GitHub. Quando disponível, o token OAuth do usuário (`token_usuario_github`) MUST ser utilizado para conferir autoria direta ao usuário no GitHub, mantendo fallback automático para a credencial do bot GitHub App caso o token do usuário não esteja presente ou seja inválido. Caso o servidor rejeite a requisição indicando violação de escopo, os arquivos apontados como inválidos MUST ser detalhados no erro reportado.

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

#### Scenario: Detalhamento Transparente de Arquivos Fora de Escopo Rejeitados
- **WHEN** a Edge Function `create-pr` rejeitar a abertura com HTTP 400 e retornar a lista `arquivos_invalidos`
- **THEN** o `ServicoSubmissao` MUST incluir os caminhos dos arquivos inválidos na mensagem de erro da exceção `ErroSubmissao` para que a interface gráfica apresente claramente a causa do bloqueio ao usuário
