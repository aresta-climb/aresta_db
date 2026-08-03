## ADDED Requirements

### Requirement: Pre-boot Independent Update Checking
The system SHALL efetuar a chamada para a API do GitHub no prólogo do aplicativo, antes de carregar frameworks pesados ou acionar o módulo de Login.

#### Scenario: Active Keyring Token
- **WHEN** o cofre do Windows (Keyring) já possui um token salvo de uma sessão de usuário passada
- **THEN** o sistema anexa este token à requisição silenciosamente, mitigando bloqueios de rede, falhando graciosamente para requisição pública caso não haja token.

### Requirement: Execution File Replacement (Rename Trick)
The system SHALL substituir o próprio binário no ambiente restrito do Windows enganando o SO via renomeação em tempo real.

#### Scenario: Downloading an update
- **WHEN** o aplicativo encontra uma versão superior no GitHub
- **THEN** ele levanta a Splash Screen nativa reportando progresso, renomeia-se para `.old.exe`, salva os novos bytes no local oficial e dá o trigger de self-restart (finalizando-se em seguida).
