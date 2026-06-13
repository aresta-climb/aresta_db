## ADDED Requirements

### Requirement: Servidor assíncrono não-bloqueante
O sistema MUST servir os recursos estáticos e o endpoint `/handshake` através de uma engine ASGI não-bloqueante (FastAPI e Uvicorn), garantindo que um cliente com conexão lenta não trave a fila de requisições do servidor local.

#### Scenario: Handshake bem sucedido
- **WHEN** o dispositivo móvel realizar um GET em `/handshake`
- **THEN** o sistema deve emitir o sinal Qt `dispositivo_conectado` de maneira thread-safe e retornar uma resposta JSON HTTP 200 com `{"status": "conectado"}`.

#### Scenario: ETag e validação de Cache Nativo
- **WHEN** o dispositivo móvel solicitar um arquivo fornecendo o cabeçalho `If-None-Match`
- **THEN** o sistema deve validar se a modificação bate através dos metadados rápidos (como `os.stat` usado por `StaticFiles`), retornando HTTP 304 Not Modified instantaneamente caso o arquivo não tenha sido alterado desde a última requisição.

#### Scenario: Desligamento Seguro
- **WHEN** o usuário ou a aplicação solicitar a parada do servidor local
- **THEN** o sistema deve notificar o servidor ASGI de forma limpa (ex: setando a flag `should_exit = True` do uvicorn) e o socket deverá ser fechado graciosamente, sem a necessidade de contornos ou abertura de novas threads para forçar shutdown.
