## ADDED Requirements

### Requirement: Verificação e Pré-preenchimento de Perfil do Autor
A aplicação MUST verificar se o autor possui nome completo cadastrado nos metadados da conta e pré-preencher com dados do GitHub quando disponíveis.

#### Scenario: Autor com Nome Completo Cadastrado
- **WHEN** o usuário se autentica e possui o campo `nome_completo` nos metadados do Supabase Auth
- **THEN** a aplicação MUST seguir diretamente para o carregamento do editor sem interrupção

#### Scenario: Autor sem Nome Completo com Login GitHub
- **WHEN** o usuário se autentica com GitHub OAuth e não possui `nome_completo` explicitamente definido
- **THEN** a aplicação MUST abrir o diálogo de perfil pré-preenchendo o campo de nome com o valor de `full_name` ou `name` retornado pelo GitHub

#### Scenario: Autor sem Nome Completo com Login E-mail OTP
- **WHEN** o usuário se autentica com E-mail OTP pela primeira vez e não possui nenhum nome cadastrado
- **THEN** a aplicação MUST exibir diálogo solicitando a inserção do Nome Completo antes de liberar o acesso

### Requirement: Atualização do Nome Completo nos Metadados
A aplicação MUST persistir o Nome Completo informado/confirmado pelo usuário na conta do Supabase Auth.

#### Scenario: Salvar Nome Completo com Sucesso
- **WHEN** o usuário confirma o diálogo de perfil com nome válido (mínimo 2 palavras)
- **THEN** a aplicação MUST enviar requisição PUT para `/auth/v1/user` com o JWT do usuário e salvar o nome nos metadados da sessão local
