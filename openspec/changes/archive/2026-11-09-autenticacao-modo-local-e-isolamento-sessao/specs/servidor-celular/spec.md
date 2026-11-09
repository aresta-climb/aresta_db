# Spec Delta

## ADDED Requirements

### Requirement: Falha Explícita sem Fallback Silencioso na Criação de Sessão de Prévia
O `ServidorCelular`, a `TarefaDadosConexao` e o `DialogoConexaoCelular` MUST operar em modo Fail-Fast ao iniciar uma sessão de Live Review, exigindo o registro bem-sucedido da sessão autenticada no Cloudflare Relay (`previa.arestaclimb.com`) ou um código de sessão válido, sendo proibido fazer fallback silencioso para URL HTTP de IP local sem código de pareamento (`---- - ----`).

#### Scenario: Falha ao obter sessão por ausência de token JWT ou erro no Cloudflare Relay
- **WHEN** o usuário abre o diálogo "Conectar ao Celular" e `solicitar_sessao_servidor()` falha por ausência de token JWT válido ou erro de comunicação com o Cloudflare Worker
- **THEN** `obter_url_previa_canonica()` MUST lançar uma exceção explícita em vez de retornar `http://<ip>:<porta>`
- **AND** a `TarefaDadosConexao` MUST emitir o sinal `erro` com a mensagem explicativa da falha
- **AND** o `DialogoConexaoCelular` MUST ocultar o spinner de carregamento e exibir claramente a mensagem de erro na interface, sem exibir QR Code inválido nem o placeholder `---- - ----` como se estivesse aguardando conexão
