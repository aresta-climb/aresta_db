## ADDED Requirements

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

### Requirement: Acionamento da Interface de Atualização da Loja
O sistema DEVE permitir ao usuário acionar a atualização oficial da Microsoft Store (via API nativa `StoreContext` ou protocolo `ms-windows-store://`).

#### Scenario: Usuário clica em Atualizar
- **WHEN** o usuário confirma o desejo de atualizar o aplicativo
- **THEN** o sistema aciona a rotina de atualização da Microsoft Store e encerra o aplicativo de forma limpa para permitir que o Windows instale o novo pacote.
