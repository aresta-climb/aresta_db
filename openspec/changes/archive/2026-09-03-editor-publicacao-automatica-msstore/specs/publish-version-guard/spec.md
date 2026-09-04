## ADDED Requirements

### Requirement: Identificador Canônico de Produto da Microsoft Store
O serviço de integração com a loja (`ServicoLoja`) DEVE (SHALL) utilizar o identificador oficial do produto `9N6CQNH78WN8` como valor canônico padrão para consultas de atualização e geração de URIs de redirecionamento.

#### Scenario: Redirecionamento por deep link sem identificador customizado
- **WHEN** o método de abertura de página na loja (`abrir_pagina_na_loja`) for acionado sem argumento explícito de produto
- **THEN** o sistema constrói a URI utilizando o protocolo `ms-windows-store://pdp/?ProductId=9N6CQNH78WN8`
- **AND** comanda a abertura da página do Editor Aresta na Microsoft Store
