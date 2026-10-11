# Spec Delta: editor-inicializacao

## ADDED Requirements

### Requirement: Etapa de Desbloqueio do Cofre de Senhas na Inicialização
A `TarefaInicializacao` da Splash Screen MUST incluir uma etapa formal de inicialização e desbloqueio do cofre de credenciais do sistema operacional executada em segundo plano antes da verificação de sessão.

#### Scenario: Notificação Visual e Desbloqueio em Segundo Plano
- **WHEN** a `TarefaInicializacao` iniciar a etapa de acesso ao cofre de senhas
- **THEN** a interface gráfica MUST atualizar a barra de progresso e exibir o status "Acessando cofre de senhas do aplicativo..."
- **AND** a aplicação MUST aguardar uma breve pausa para leitura do usuário antes de disparar a solicitação ao cofre no sistema operacional
- **AND** a requisição MUST ser executada em thread separada da interface gráfica para manter a janela responsiva

#### Scenario: Desbloqueio Concluído com Sucesso
- **WHEN** o cofre do sistema estiver destrancado ou o usuário fornecer a senha com sucesso no diálogo nativo
- **THEN** a aplicação MUST registrar o cofre como operacional e prosseguir para a verificação de autenticação

#### Scenario: Desbloqueio Cancelado pelo Usuário
- **WHEN** o usuário cancelar explicitamente o diálogo de senha do sistema operacional
- **THEN** a aplicação MUST registrar o cofre como não operacional, ativar a retenção de sessão temporária em memória RAM e prosseguir com a inicialização
