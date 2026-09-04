# publish-version-guard Specification

## Purpose
Garante que o Aresta Editor seja executado em versões sincronizadas com a Microsoft Store, prevenindo inconsistências de dados no banco de dados comunitário através de verificação no boot e guarda na publicação.

## Requirements
### Requirement: Verificação de Atualização na Microsoft Store no Boot
O sistema DEVE verificar se existem atualizações disponíveis na Microsoft Store durante o processo de inicialização do aplicativo (`TelaDeAbertura`).

#### Scenario: Atualização disponível na Loja na inicialização
- **WHEN** o aplicativo é iniciado em ambiente empacotado MSIX e existe uma versão mais recente na Microsoft Store
- **THEN** o sistema exibe aviso na tela de abertura informando sobre a atualização e oferece opção para disparar a atualização na Microsoft Store antes de abrir o editor.

#### Scenario: Execução em ambiente de desenvolvimento local
- **WHEN** o aplicativo é executado diretamente via Python (sem identidade de pacote MSIX)
- **THEN** o sistema ignora a checagem da Microsoft Store graciosamente e prossegue com a inicialização normal.

### Requirement: Bloqueio de Publicação por Versão Desatualizada
O sistema DEVE validar a versão do editor junto à Microsoft Store antes de permitir a publicação de alterações no banco de dados.

#### Scenario: Usuário tenta publicar com versão defasada
- **WHEN** o usuário clica em "Publicar" e o aplicativo detecta que uma versão mais recente está disponível na Microsoft Store
- **THEN** o sistema cancela a publicação, exibe diálogo explicativo e direciona o usuário para atualizar o aplicativo na Microsoft Store.

### Requirement: Acionamento da Interface de Atualização da Loja (Estratégia Híbrida)
O sistema DEVE permitir ao usuário acionar a atualização oficial da Microsoft Store, priorizando a interface in-app e recorrendo ao deep link como fallback.

#### Scenario: Atualização in-app bem-sucedida
- **WHEN** o usuário clica em "Atualizar" e a API WinRT está acessível
- **THEN** o sistema aciona `RequestDownloadAndInstallStorePackageUpdatesAsync`, exibindo a interface modal do Windows com progresso do download sobreposta ao app.

#### Scenario: Fallback para deep link da Loja
- **WHEN** a chamada in-app da API WinRT falha ou não está disponível
- **THEN** o sistema abre a página do aplicativo na Microsoft Store via `ms-windows-store://pdp/?ProductId=...` e encerra a aplicação de forma limpa para permitir que a Loja conclua a instalação sem lock de arquivo.

### Requirement: Identificador Canônico de Produto da Microsoft Store
O serviço de integração com a loja (`ServicoLoja`) DEVE (SHALL) utilizar o identificador oficial do produto `9N6CQNH78WN8` como valor canônico padrão para consultas de atualização e geração de URIs de redirecionamento.

#### Scenario: Redirecionamento por deep link sem identificador customizado
- **WHEN** o método de abertura de página na loja (`abrir_pagina_na_loja`) for acionado sem argumento explícito de produto
- **THEN** o sistema constrói a URI utilizando o protocolo `ms-windows-store://pdp/?ProductId=9N6CQNH78WN8`
- **AND** comanda a abertura da página do Editor Aresta na Microsoft Store
