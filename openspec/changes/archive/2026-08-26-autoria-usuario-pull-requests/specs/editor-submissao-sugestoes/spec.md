## MODIFIED Requirements

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
