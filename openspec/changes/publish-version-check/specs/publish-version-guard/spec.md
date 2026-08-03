## ADDED Requirements

### Requirement: Block publish on outdated version
The system SHALL intercept the publish action to verify the editor's semantic version against the latest GitHub Release, blocking the user se estiver desatualizado.

#### Scenario: User attempts to publish with an old editor
- **WHEN** o usuário clica em "Publicar" estando em uma instância desatualizada do editor
- **THEN** o sistema cancela imediatamente a criação da Pull Request (ou qualquer fluxo local preparatório) e alerta o usuário sobre a defasagem.

### Requirement: Asynchronous API check
The system SHALL realizar a verificação de versão da API do GitHub sem bloquear a Thread principal gráfica (Main UI Thread).

#### Scenario: Network delay during check
- **WHEN** a rede demora a responder a consulta à API do GitHub
- **THEN** a tela de carregamento "Verificando versão..." é mantida, e a interface principal não fica como "Não Respondendo" no Windows.

### Requirement: Seamless App Restart
The system SHALL prover um mecanismo de UI direto para que o aplicativo seja reiniciado pelo usuário a fim de forçar o fluxo de atualização (boot).

#### Scenario: User acknowledges the block and decides to restart
- **WHEN** o usuário recebe a notificação de versão antiga e clica no botão explícito de "Reiniciar"
- **THEN** o sistema comanda um graceful exit do processo atual abrindo uma sub-rotina para invocar o aplicativo limpo e forçar as engrenagens de boot da Fase 3 a girarem.
