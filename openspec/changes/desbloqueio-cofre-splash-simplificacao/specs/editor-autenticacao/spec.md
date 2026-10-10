# Spec Delta: editor-autenticacao

## MODIFIED Requirements

### Requirement: Verificação de Disponibilidade do Cofre de Senhas
O sistema MUST consolidar o acesso ao cofre em etapa única na inicialização e alertar o usuário com aviso de sessão temporária apenas quando o desbloqueio do cofre for cancelado ou falhar.

#### Scenario: Cofre trancado ou inacessível na tela de autenticação
- **WHEN** a tela de abertura apresentar a tela de autenticação e o cofre do sistema não tiver sido desbloqueado pelo usuário durante a etapa de inicialização
- **THEN** a interface MUST exibir uma mensagem de aviso informativa: "O cofre de senhas não foi desbloqueado (ação cancelada). Você pode fazer login normalmente, mas sua sessão só será lembrada durante esta execução do app."
- **AND** a aplicação MUST permitir que o usuário faça login normalmente utilizando retenção de sessão em memória RAM durante a execução atual

#### Scenario: Cofre desbloqueado e operacional
- **WHEN** a tela de abertura apresentar a tela de autenticação e o cofre do sistema tiver sido desbloqueado na inicialização
- **THEN** a interface MUST ocultar qualquer aviso sobre cofre e persistir as credenciais normalmente no cofre
