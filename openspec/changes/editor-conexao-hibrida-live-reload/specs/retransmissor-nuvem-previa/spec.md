## ADDED Requirements

### Requirement: Registro e gerenciamento de sessões efêmeras
O Cloudflare Worker em `previa.arestaclimb.com` MUST permitir que instâncias do Aresta Editor registrem sessões efêmeras identificadas por códigos alfanuméricos de 8 caracteres em Base36 (`[0-9a-z]`), mantendo o estado de conexão e metadados exclusivamente em memória RAM.

#### Scenario: Registro de nova sessão pelo editor
- **WHEN** o Editor Desktop estabelecer uma conexão WebSocket com `wss://previa.arestaclimb.com/ws?sessao=<codigo>` e enviar a mensagem inicial de registro com metadados de rede local
- **THEN** o Worker deve armazenar a sessão em memória vinculando o socket do editor e responder com confirmação de registro com sucesso.

#### Scenario: Rejeição de código duplicado
- **WHEN** um editor tentar registrar um código de sessão que já está ativo em outra conexão
- **THEN** o Worker deve rejeitar a conexão com código de encerramento adequado ou erro indicando colisão.

### Requirement: Proxy reverso de streaming HTTP para WebSocket
O Cloudflare Worker MUST interceptar requisições HTTP enviadas pelo aplicativo móvel para `https://previa.arestaclimb.com/<codigo>/*`, encaminhar a solicitação via WebSocket para o Editor Desktop conectado e transmitir a resposta de volta ao aplicativo móvel sem gravar dados em disco ou banco.

#### Scenario: Encaminhamento de requisição de arquivo estático ou protobuf
- **WHEN** o aplicativo móvel fizer um `GET https://previa.arestaclimb.com/<codigo>/indice.binarypb`
- **THEN** o Worker deve encapsular a requisição em uma mensagem WebSocket, enviá-la ao editor, aguardar os bytes de resposta e retorná-los como resposta HTTP com status code e headers correspondentes.

#### Scenario: Requisição para sessão inexistente ou expirada
- **WHEN** o aplicativo móvel fizer uma requisição para um código de sessão que não está registrado ou que já foi finalizado
- **THEN** o Worker deve retornar imediatamente status HTTP 404 com mensagem JSON informativa.

### Requirement: Intermediário de metadados de rede local e handshake
O Cloudflare Worker MUST fornecer um endpoint de informações da sessão (`GET /<codigo>/info` ou `GET /<codigo>/handshake`) retornando os metadados de rede local do editor para viabilizar a disputa (*race*) de rede pelo aplicativo móvel.

#### Scenario: Consulta de metadados da sessão ativa
- **WHEN** um cliente consultar as informações de uma sessão ativa através de `GET /<codigo>/info`
- **THEN** o Worker deve responder com JSON contendo o status da sessão e a URL local anunciada pelo editor (`local_url`).

### Requirement: Encerramento automático e Batimento Cardíaco
O Cloudflare Worker MUST encerrar e liberar a sessão imediatamente ao fechar a conexão WebSocket do editor, ao detectar perda de batimento cardíaco (ping/pong a cada 30 segundos) ou ao atingir o tempo limite de inatividade configurado (20 a 30 minutos).

#### Scenario: Desconexão limpa do editor
- **WHEN** o editor fechar a conexão WebSocket de forma voluntária
- **THEN** o Worker deve remover imediatamente a sessão da memória e rejeitar quaisquer requisições subsequentes para aquele código com HTTP 404.
