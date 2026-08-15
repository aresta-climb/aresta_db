## MODIFIED Requirements

### Requirement: Uso de Biblioteca Git Embarcada
A aplicação MUST realizar operações Git utilizando `pygit2` para evitar dependência do binário `git` no sistema operacional. Adicionalmente, as operações de clonagem MUST configurar a biblioteca para habilitar nativamente caminhos longos antes do checkout.

#### Scenario: Execução em Máquina Limpa
- **WHEN** o usuário não possuir o binário Git instalado
- **THEN** a aplicação MUST ser capaz de realizar clone e fetch usando a biblioteca nativa embarcada

#### Scenario: Proteção contra Limite de Caracteres no Clone
- **WHEN** a aplicação iniciar a clonagem do repositório base
- **THEN** o sistema MUST inicializar o repositório manualmente e injetar a configuração `core.longpaths = True`
- **THEN** o sistema MUST realizar o `fetch` e `checkout` somente após a configuração ter sido aplicada
