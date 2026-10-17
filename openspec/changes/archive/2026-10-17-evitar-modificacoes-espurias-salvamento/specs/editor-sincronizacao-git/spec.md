## MODIFIED Requirements

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
- **WHEN** a aplicação iniciar a clonagem, sincronização (`fazer_checkout_main_upstream`) do repositório base ou a inicialização de um repositório de croqui experimental
- **THEN** o sistema MUST configurar explicitamente `core.autocrlf = False` na configuração local do repositório antes do `checkout`, garantindo que os arquivos na árvore de trabalho utilizem `LF`
