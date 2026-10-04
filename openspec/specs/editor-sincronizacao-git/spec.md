# editor-sincronizacao-git Specification

## Purpose
TBD - created by archiving change tela-de-abertura. Update Purpose after archive.
## Requirements
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
A aplicação MUST realizar operações Git utilizando `pygit2` para evitar dependência do binário `git` no sistema operacional. Adicionalmente, as operações de clonagem MUST configurar a biblioteca para habilitar nativamente caminhos longos antes do checkout.

#### Scenario: Execução em Máquina Limpa
- **WHEN** o usuário não possuir o binário Git instalado
- **THEN** a aplicação MUST ser capaz de realizar clone e fetch usando a biblioteca nativa embarcada

#### Scenario: Proteção contra Limite de Caracteres no Clone
- **WHEN** a aplicação iniciar a clonagem do repositório base
- **THEN** o sistema MUST inicializar o repositório manualmente e injetar a configuração `core.longpaths = True`
- **THEN** o sistema MUST realizar o `fetch` e `checkout` somente após a configuração ter sido aplicada

### Requirement: Resiliência e Degradação Graciosa na Sincronização Remota
A aplicação MUST tratar falhas de rede, timeouts de conexão e erros de transporte durante a sincronização remota sem interromper a execução quando o repositório local já existir no disco.

#### Scenario: Falha de Conexão com Base Local Existente
- **WHEN** o comando de `fetch` remoto falhar por timeout, desconexão ou falha de canal seguro e o repositório local já estiver presente
- **THEN** a aplicação MUST suprimir o encerramento do processo
- **THEN** a aplicação MUST emitir um aviso informativo de operação em modo offline e continuar a inicialização

#### Scenario: Tratamento de Credenciais em Repositório Público
- **WHEN** o usuário realizar clone ou fetch no repositório base público
- **THEN** a aplicação MUST abster-se de injetar tokens de autorização de usuário propensos a expiração
- **THEN** caso a biblioteca subjacente consulte o callback de credenciais sem token disponível, o sistema MUST sinalizar `Passthrough` em vez de retornar valor nulo

#### Scenario: Diagnóstico Legível de Falhas do Git
- **WHEN** o motor Git nativo reportar um erro genérico com mensagem vazia ou "no error" decorrente de esgotamento de tentativas no Windows
- **THEN** a biblioteca de sincronização MUST traduzir a exceção para um `ErroSincronizacaoGit` com mensagem clara indicando tempo limite esgotado ou falha de conexão de rede


