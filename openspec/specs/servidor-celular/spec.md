# servidor-celular Specification

## Purpose

Define o servidor HTTP local e a integração com o túnel de retransmissão WebSocket do Editor Desktop para servir artefatos compilados e eventos de recarregamento ao aplicativo móvel.

## Requirements

### Requirement: Integração com Túnel de Saída para o Retransmissor
O servidor local do Editor Desktop MUST estabelecer e manter a conexão de saída WebSocket com o Retransmissor na nuvem (`wss://previa.arestaclimb.com/ws?sessao=<codigo>`) de forma contínua durante todo o ciclo de vida da sessão do Editor Desktop, mantendo o túnel aberto mesmo na ausência de dispositivos móveis pareados, até o encerramento explícito pelo usuário ou fechamento do workspace.

#### Scenario: Manutenção contínua do túnel sem dispositivos conectados
- **WHEN** o servidor celular for iniciado no Editor Desktop e nenhum dispositivo móvel estiver conectado
- **THEN** o túnel com o Cloudflare Worker deve permanecer ativo, conectado e pronto para responder a conexões e requisições remotas a qualquer momento.

#### Scenario: Encerramento explícito do túnel
- **WHEN** o usuário clicar no botão de encerrar conexão ou fechar o croqui atual
- **THEN** o `ServidorCelular` deve finalizar graciosamente a conexão WebSocket com o retransmissor e liberar os recursos de rede.

### Requirement: Resolução Resiliente de Rotas Compactadas
O servidor HTTP local (`ServidorCelular`) e o cliente do túnel de retransmissão (`ClienteTunelRetransmissor`) MUST resolver requisições no formato `<id_croqui>/<caminho_relativo>` fazendo fallback direto para `<pasta_compilado>/<caminho_relativo>` sempre que `<pasta_compilado>/<id_croqui>/<caminho_relativo>` não for um arquivo existente e `<pasta_compilado>/<caminho_relativo>` for um arquivo válido, independentemente de o diretório `<pasta_compilado>/<id_croqui>` existir transitoriamente no disco.

#### Scenario: Download de imagem ou binário durante ou após compactação da pasta compilado
- **WHEN** o aplicativo móvel solicita `<id_croqui>/imagens/<foto>.webp` ou `<id_croqui>/compilado.binarypb` via HTTP local ou túnel WebSocket
- **AND** o arquivo reside na raiz compactada (`<pasta_compilado>/imagens/<foto>.webp` ou `<pasta_compilado>/compilado.binarypb`), mesmo que uma subpasta `<pasta_compilado>/<id_croqui>` exista vazia ou parcialmente movida durante a compilação
- **THEN** o servidor deve localizar e retornar o arquivo da raiz compactada com status HTTP 200 (ou 304 se `ETag` coincidir), sem retornar erro HTTP 404
