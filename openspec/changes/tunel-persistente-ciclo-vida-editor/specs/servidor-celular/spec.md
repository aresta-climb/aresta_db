## MODIFIED Requirements

### Requirement: Integração com Túnel de Saída para o Retransmissor
O servidor local do Editor Desktop MUST estabelecer e manter a conexão de saída WebSocket com o Retransmissor na nuvem (`wss://previa.arestaclimb.com/ws?sessao=<codigo>`) de forma contínua durante todo o ciclo de vida da sessão do Editor Desktop, mantendo o túnel aberto mesmo na ausência de dispositivos móveis pareados, até o encerramento explícito pelo usuário ou fechamento do workspace.

#### Scenario: Manutenção contínua do túnel sem dispositivos conectados
- **WHEN** o servidor celular for iniciado no Editor Desktop e nenhum dispositivo móvel estiver conectado
- **THEN** o túnel com o Cloudflare Worker deve permanecer ativo, conectado e pronto para responder a conexões e requisições remotas a qualquer momento.

#### Scenario: Encerramento explícito do túnel
- **WHEN** o usuário clicar no botão de encerrar conexão ou fechar o croqui atual
- **THEN** o `ServidorCelular` deve finalizar graciosamente a conexão WebSocket com o retransmissor e liberar os recursos de rede.
