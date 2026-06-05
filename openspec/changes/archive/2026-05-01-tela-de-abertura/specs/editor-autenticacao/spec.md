## ADDED Requirements

### Requirement: Autenticação via GitHub Device Flow
O sistema MUST permitir que o usuário se autentique no GitHub através do Device Flow.

#### Scenario: Novo Login
- **WHEN** o usuário não estiver autenticado ou o token for inválido
- **THEN** a `TelaDeAbertura` MUST exibir um texto explicativo longo, um código de 8 dígitos e um botão para abrir o GitHub
- **THEN** o texto explicativo MUST detalhar a finalidade da conexão (recuperar e publicar croquis)

### Requirement: Persistência de Credenciais
O sistema MUST armazenar o token de acesso de forma segura no sistema operacional via `keyring`.

#### Scenario: Armazenamento em Keyring
- **WHEN** um novo token for obtido
- **THEN** a aplicação MUST salvar o token de forma persistente e criptografada via sistema operacional

### Requirement: Validação de Token Existente
A aplicação MUST validar o token armazenado durante a inicialização antes de prosseguir para a sincronização.

#### Scenario: Verificação de Validade
- **WHEN** um token for encontrado no storage local
- **THEN** a aplicação MUST realizar uma chamada de teste à API do GitHub para garantir que o token ainda é válido
