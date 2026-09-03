# retransmissor-nuvem-previa

### Requirement: Registro e gerenciamento de sessões efêmeras
O Cloudflare Worker em `previa.arestaclimb.com` MUST permitir que instâncias do Aresta Editor registrem e restaurem sessões de prévia identificadas por códigos alfanuméricos de 8 caracteres em Base36 (`[0-9a-z]`), mantendo o estado de conexão ativo e tolerante a reinicializações de container (*cold starts*).

#### Scenario: Registro de nova sessão pelo editor
- **WHEN** o Editor Desktop estabelecer uma conexão com `POST /sessoes` ou conectar diretamente via WebSocket `wss://previa.arestaclimb.com/ws?sessao=<codigo>&token=<jwt>` com token JWT válido
- **THEN** o Worker deve registrar e vincular a sessão ao código informado e ao usuário autenticado, aceitando a conexão WebSocket sem retornar erro 404.

#### Scenario: Auto-restauração de sessão após reinício do Worker
- **WHEN** o Editor Desktop reconectar ao WebSocket `wss://previa.arestaclimb.com/ws?sessao=<codigo>&token=<jwt>` e a sessão não estiver presente na memória RAM (devido a reinicialização ou descarregamento do Durable Object)
- **THEN** o Worker deve validar o token JWT e recriar/restaurar automaticamente a sessão para o código solicitado, mantendo o mesmo identificador acessível para clientes móveis.

### Requirement: Encerramento automático e Batimento Cardíaco
O Cloudflare Worker MUST manter a sessão ativa enquanto o Editor Desktop estiver conectado ou dentro da janela de tolerância de reconexão de 10 minutos, tratando desconexões e inatividade de clientes móveis como ocorrências efêmeras que não encerram a sessão.

#### Scenario: Desconexão temporária do editor com reconexão dentro da tolerância
- **WHEN** o WebSocket do Editor Desktop desconectar momentaneamente e reconectar dentro de até 10 minutos
- **THEN** o Worker deve preservar os dados da sessão e restabelecer o túnel de streaming sem descartar o código de pareamento.

#### Scenario: Desconexão ou ausência de clientes móveis
- **WHEN** nenhum aplicativo móvel estiver conectado ou os clientes móveis fecharem seus WebSockets de eventos
- **THEN** o Worker deve manter a sessão e o túnel do Editor Desktop perfeitamente operacionais, permitindo que novos clientes móveis conectem a qualquer momento pelo mesmo código.

### Requirement: Persistência de metadados no Storage do Durable Object
O Durable Object de sessão MUST salvar o registro essencial de identificação da sessão (`codigo`, `usuarioId`, `criadoEm`, `metadados`) em seu Storage nativo (`state.storage`).

#### Scenario: Recuperação de metadados a partir do storage
- **WHEN** uma requisição de metadados (`GET /<codigo>/info`) ou conexão de eventos (`GET /<codigo>/events`) for recebida e o estado não estiver na memória RAM mas existir no Storage do Durable Object
- **THEN** o Worker deve carregar os metadados do storage e atender à requisição normalmente.
