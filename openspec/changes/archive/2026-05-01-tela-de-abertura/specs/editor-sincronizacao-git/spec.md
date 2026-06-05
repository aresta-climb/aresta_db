## ADDED Requirements

### Requirement: Sincronização Inteligente do Repositório Base
A aplicação MUST garantir que o repositório `aresta-climb/aresta_db` local esteja sincronizado.

#### Scenario: Usuário sem Permissão de Escrita
- **WHEN** o usuário não tiver permissão de escrita no repositório `aresta-climb/aresta_db`
- **THEN** a aplicação MUST criar um fork do repositório na conta do usuário via API
- **THEN** a aplicação MUST clonar o fork localmente e configurar o original como `upstream`

#### Scenario: Repositório Privado
- **WHEN** o repositório for privado e o usuário tentar sincronizar
- **THEN** a aplicação MUST injetar o token OAuth2 nas requisições do `pygit2` para permitir o acesso
- **THEN** se o acesso for negado (404/401), a aplicação MUST reportar o erro com instruções de autorização

#### Scenario: Progresso da Sincronização
- **WHEN** uma operação de clone ou pull estiver em andamento
- **THEN** a `TelaDeAbertura` MUST exibir o progresso em tempo real na barra de progresso estilizada

### Requirement: Uso de Biblioteca Git Embarcada
A aplicação MUST realizar operações Git utilizando `pygit2` para evitar dependência do binário `git` no sistema operacional.

#### Scenario: Execução em Máquina Limpa
- **WHEN** o usuário não possuir o binário Git instalado
- **THEN** a aplicação MUST ser capaz de realizar clone e fetch usando a biblioteca nativa embarcada
