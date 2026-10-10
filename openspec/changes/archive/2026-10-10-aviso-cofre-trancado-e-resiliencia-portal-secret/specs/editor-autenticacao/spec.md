# Spec Delta

## ADDED Requirements

### Requirement: Verificação de Disponibilidade do Cofre de Senhas
O sistema MUST verificar a disponibilidade e acessibilidade do cofre do sistema operacional antes da autenticação e alertar o usuário caso esteja trancado ou inacessível.

#### Scenario: Cofre trancado ou inacessível na tela de autenticação
- **WHEN** a tela de abertura apresentar a tela de autenticação e o cofre do sistema estiver trancado ou inacessível
- **THEN** a interface MUST exibir uma mensagem de aviso informativa antes do login: "Cofre do sistema está trancado; para que sua sessão seja lembrada na próxima vez que abrir o app, desbloqueie o cofre de senhas do sistema."
- **AND** a aplicação MUST permitir que o usuário faça login normalmente utilizando retenção de sessão em memória RAM durante a execução atual

#### Scenario: Cofre desbloqueado e operacional
- **WHEN** a tela de abertura apresentar a tela de autenticação e o cofre do sistema estiver acessível
- **THEN** a interface MUST ocultar qualquer aviso sobre cofre trancado e persistir as credenciais normalmente no chaveiro

## MODIFIED Requirements

### Requirement: Persistência de Credenciais
O sistema MUST armazenar a sessão do usuário de forma segura no sistema operacional via `keyring` ou reter em memória caso o cofre esteja indisponível.

#### Scenario: Armazenamento de Sessão Unificada em Keyring
- **WHEN** um novo login for concluído (via E-mail OTP ou GitHub)
- **THEN** a aplicação MUST salvar o token JWT do Supabase, o refresh token e os dados do usuário de forma persistente e criptografada via sistema operacional

#### Scenario: Fallback para Sessão em Memória quando Cofre Indisponível
- **WHEN** um novo login for concluído mas o cofre do sistema estiver trancado ou inacessível
- **THEN** a aplicação MUST reter os dados da sessão em memória para uso contínuo durante a execução atual do aplicativo
