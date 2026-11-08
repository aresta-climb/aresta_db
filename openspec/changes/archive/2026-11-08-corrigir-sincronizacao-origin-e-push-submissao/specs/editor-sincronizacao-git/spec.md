## MODIFIED Requirements

### Requirement: Sincronização Inteligente do Repositório Base
A aplicação MUST garantir que o repositório `aresta-climb/aresta_db` local esteja sincronizado utilizando exclusivamente o remote oficial `origin` (`refs/remotes/origin/main`), removendo remotes legados (`upstream`) ou efêmeros (`proxy`) durante a configuração.

#### Scenario: Usuário sem Permissão de Escrita
- **WHEN** o usuário não tiver permissão de escrita direta no repositório `aresta-climb/aresta_db`
- **THEN** a aplicação MUST sincronizar o repositório local diretamente a partir do remote oficial `origin` sem criar forks e sem configurar o remote `upstream`

#### Scenario: Configuração Unificada em Origin e Limpeza de Remotes Legados
- **WHEN** a aplicação configurar os remotes do repositório base local (`configurar_remotes`)
- **THEN** a aplicação MUST garantir a existência do remote `origin` apontando para a URL oficial do repositório base
- **THEN** caso existam os remotes `upstream` ou `proxy` no repositório local, a aplicação MUST removê-los juntamente com suas referências remotas associadas

#### Scenario: Fetch Exclusivo do Remote Origin
- **WHEN** a aplicação executar a busca de atualizações remotas (`fazer_fetch`)
- **THEN** a aplicação MUST realizar o `fetch` exclusivamente do remote `origin`, atualizando `refs/remotes/origin/main`

#### Scenario: Repositório Privado
- **WHEN** o repositório for privado e o usuário tentar sincronizar
- **THEN** a aplicação MUST injetar o token OAuth2 nas requisições do `pygit2` para permitir o acesso
- **THEN** se o acesso for negado (404/401), a aplicação MUST reportar o erro com instruções de autorização

#### Scenario: Progresso da Sincronização
- **WHEN** uma operação de clone ou pull estiver em andamento
- **THEN** a `TelaDeAbertura` MUST exibir o progresso em tempo real na barra de progresso estilizada

### Requirement: Uso de Biblioteca Git Embarcada
A aplicação MUST realizar operações Git utilizando `pygit2` para evitar dependência do binário `git` no sistema operacional. Adicionalmente, as operações de inicialização, clonagem e sincronização MUST configurar o repositório para habilitar nativamente caminhos longos (`core.longpaths = True`) e desabilitar a conversão automática de quebras de linha (`core.autocrlf = False`) antes do checkout.

#### Scenario: Execução em Máquina Limpa
- **WHEN** o usuário não possuir o binário Git instalado
- **THEN** a aplicação MUST ser capaz de realizar clone e fetch usando a biblioteca nativa embarcada

#### Scenario: Proteção contra Limite de Caracteres no Clone
- **WHEN** a aplicação iniciar a clonagem do repositório base
- **THEN** o sistema MUST inicializar o repositório manualmente e injetar a configuração `core.longpaths = True`
- **THEN** o sistema MUST realizar o `fetch` e `checkout` somente após a configuração ter sido aplicada

#### Scenario: Proteção contra Conversão CRLF no Clone e Checkout
- **WHEN** a aplicação iniciar a clonagem, a sincronização da branch principal do repositório base a partir de `origin/main` ou a inicialização de um repositório de croqui experimental
- **THEN** o sistema MUST configurar explicitamente `core.autocrlf = False` na configuração local do repositório antes do `checkout` sobre o alvo de `origin/main`, garantindo que os arquivos na árvore de trabalho utilizem `LF`
