## ADDED Requirements

### Requirement: Heartbeat assíncrono não destrutivo no cliente Desktop
A biblioteca `ClienteTunelRetransmissor` MUST executar o envio de pings periódicos de *heartbeat* em uma rotina assíncrona dedicada em segundo plano, sem interromper ou cancelar tarefas ativas de leitura `ws.recv()`.

#### Scenario: Envio de keepalive com canal ocioso
- **WHEN** o túnel WebSocket estiver conectado e nenhum tráfego de requisições proxy estiver sendo trafegado pelo canal
- **THEN** o cliente desktop deve emitir pings periódicos mantendo a conexão aberta com o Cloudflare Worker sem provocar exceções de cancelamento na escuta de mensagens.

### Requirement: Reconexão e auto-recuperação transparente do código de sessão
A biblioteca `ClienteTunelRetransmissor` MUST tentar reconectar automaticamente em caso de queda de rede, renovando o token JWT quando necessário e mantendo inalterado o código de sessão de 8 caracteres (`[0-9a-z]`).

#### Scenario: Reconexão com preservação de código
- **WHEN** ocorrer uma perda temporária de conectividade com a internet no computador do usuário
- **THEN** o cliente do túnel deve tentar reconectar em intervalos exponenciais com o mesmo código de sessão até o restabelecimento da conexão ou parada explícita.
