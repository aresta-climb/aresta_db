# Delta de Especificação: editor-autenticacao

## MODIFIED Requirements

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
