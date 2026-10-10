# editor-autenticacao Specification

## Purpose

Gerencia a autenticação segura do usuário no Aresta Editor, integrando fluxos de login por E-mail OTP e Supabase OAuth com o GitHub, além de persistência e validação contínua de credenciais de sessão.

## Requirements

### Requirement: Persistência de Credenciais
O sistema MUST armazenar a sessão do usuário de forma segura no sistema operacional via `keyring` ou reter em memória caso o cofre esteja indisponível.

#### Scenario: Armazenamento de Sessão Unificada em Keyring
- **WHEN** um novo login for concluído (via E-mail OTP ou GitHub)
- **THEN** a aplicação MUST salvar o token JWT do Supabase, o refresh token e os dados do usuário de forma persistente e criptografada via sistema operacional

#### Scenario: Fallback para Sessão em Memória quando Cofre Indisponível
- **WHEN** um novo login for concluído mas o cofre do sistema estiver trancado ou inacessível
- **THEN** a aplicação MUST reter os dados da sessão em memória para uso contínuo durante a execução atual do aplicativo

### Requirement: Verificação de Disponibilidade do Cofre de Senhas
O sistema MUST verificar a disponibilidade e acessibilidade do cofre do sistema operacional antes da autenticação e alertar o usuário caso esteja trancado ou inacessível.

#### Scenario: Cofre trancado ou inacessível na tela de autenticação
- **WHEN** a tela de abertura apresentar a tela de autenticação e o cofre do sistema estiver trancado ou inacessível
- **THEN** a interface MUST exibir uma mensagem de aviso informativa antes do login: "Cofre do sistema está trancado; para que sua sessão seja lembrada na próxima vez que abrir o app, desbloqueie o cofre de senhas do sistema."
- **AND** a aplicação MUST permitir que o usuário faça login normalmente utilizando retenção de sessão em memória RAM durante a execução atual

#### Scenario: Cofre desbloqueado e operacional
- **WHEN** a tela de abertura apresentar a tela de autenticação e o cofre do sistema estiver acessível
- **THEN** a interface MUST ocultar qualquer aviso sobre cofre trancado e persistir as credenciais normalmente no chaveiro

### Requirement: Validação de Token Existente
A aplicação MUST validar a sessão armazenada durante a inicialização antes de prosseguir.

#### Scenario: Verificação de Validade de Sessão
- **WHEN** uma sessão for encontrada no keyring local
- **THEN** a aplicação MUST validar se o JWT é válido e executar a renovação transparente via refresh token caso esteja expirado

### Requirement: Login Primário por E-mail OTP
O sistema MUST permitir que o usuário se autentique informando seu e-mail e validando o código de 6 dígitos enviado pelo Supabase Auth, controlando a frequência de solicitações via janela deslizante de 6 envios por minuto.

#### Scenario: Envio de Código OTP
- **WHEN** o usuário informa um e-mail válido e solicita o envio do código
- **THEN** a aplicação MUST enviar requisição POST para o endpoint `/auth/v1/otp` do Supabase Auth e transicionar para o estado de inserção do código

#### Scenario: Janela Deslizante de Reenvio de Código OTP
- **WHEN** o usuário solicita o reenvio de código de acesso
- **THEN** a aplicação MUST permitir até 6 solicitações de envio dentro de uma janela móvel de 60 segundos
- **AND** a aplicação MUST desabilitar o botão de reenvio exibindo contagem regressiva em segundos até a liberação da vaga mais antiga quando o limite de 6 envios na janela for atingido

#### Scenario: Validação do Código OTP com Sucesso
- **WHEN** o usuário digita o código correto de 6 dígitos
- **THEN** a aplicação MUST validar via POST `/auth/v1/verify`, obter o JWT do Supabase e prosseguir com a sessão do usuário

#### Scenario: Código OTP Inválido ou Expirado
- **WHEN** o usuário digita um código incorreto
- **THEN** a aplicação MUST exibir mensagem de erro amigável e permitir nova tentativa ou reenvio

### Requirement: Login Secundário com GitHub via Supabase OAuth
O sistema MUST permitir que mantenedores se autentiquem com o GitHub através do Supabase OAuth integrado ao GitHub App oficial.

#### Scenario: Fluxo OAuth com Navegador e Servidor Local
- **WHEN** o usuário seleciona a opção "Entrar com GitHub"
- **THEN** a aplicação MUST iniciar um servidor HTTP local efêmero em localhost, abrir o navegador na URL de autorização do Supabase e capturar o JWT do Supabase e o token do GitHub
