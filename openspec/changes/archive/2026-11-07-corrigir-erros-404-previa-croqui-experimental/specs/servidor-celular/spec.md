## ADDED Requirements

### Requirement: Resolução Resiliente de Rotas Compactadas
O servidor HTTP local (`ServidorCelular`) e o cliente do túnel de retransmissão (`ClienteTunelRetransmissor`) MUST resolver requisições no formato `<id_croqui>/<caminho_relativo>` fazendo fallback direto para `<pasta_compilado>/<caminho_relativo>` sempre que `<pasta_compilado>/<id_croqui>/<caminho_relativo>` não for um arquivo existente e `<pasta_compilado>/<caminho_relativo>` for um arquivo válido, independentemente de o diretório `<pasta_compilado>/<id_croqui>` existir transitoriamente no disco.

#### Scenario: Download de imagem ou binário durante ou após compactação da pasta compilado
- **WHEN** o aplicativo móvel solicita `<id_croqui>/imagens/<foto>.webp` ou `<id_croqui>/compilado.binarypb` via HTTP local ou túnel WebSocket
- **AND** o arquivo reside na raiz compactada (`<pasta_compilado>/imagens/<foto>.webp` ou `<pasta_compilado>/compilado.binarypb`), mesmo que uma subpasta `<pasta_compilado>/<id_croqui>` exista vazia ou parcialmente movida durante a compilação
- **THEN** o servidor deve localizar e retornar o arquivo da raiz compactada com status HTTP 200 (ou 304 se `ETag` coincidir), sem retornar erro HTTP 404
