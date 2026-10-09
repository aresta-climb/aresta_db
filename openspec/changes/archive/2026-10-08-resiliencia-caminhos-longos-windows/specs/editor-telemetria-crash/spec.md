# Spec Delta

## MODIFIED Requirements

### Requirement: Sanitização de Dados Sensíveis e Nomes de Usuário (PII)
O sistema SHALL sanitizar todos os eventos e breadcrumbs antes do envio ao Sentry através do interceptador `before_send`, substituindo caminhos absolutos do sistema operacional contendo nomes de usuários por `%APPDATA%`, `%LOCALAPPDATA%` ou `%USERPROFILE%` (suportando tanto barras simples normais/invertidas quanto barras duplas escapadas em strings serializadas), e removendo quaisquer tokens de autenticação ou credenciais sensíveis.

#### Scenario: Sanitização de caminhos no Windows
- **WHEN** uma mensagem de log ou stack trace contém o caminho `C:\Users\joaosilva\AppData\Roaming\editor_aresta\croquis\setor.yaml`
- **THEN** o interceptador `before_send` substitui o trecho pelo caminho sanitizado `%APPDATA%\editor_aresta\croquis\setor.yaml` antes de realizar o envio.

#### Scenario: Sanitização de caminhos com barras duplas escapadas
- **WHEN** uma mensagem de erro contém caminhos serializados via `repr()`, listas, tuplas ou exceções (ex: `C:\\Users\\joaosilva\\AppData\\Local\\Packages\\...`)
- **THEN** o interceptador `before_send` substitui o trecho escapado pelo identificador sanitizado correspondente (`%LOCALAPPDATA%\\Packages\\...`) sem vazar o nome de usuário local.

#### Scenario: Sanitização de tokens de autenticação
- **WHEN** um token do GitHub (`ghp_...` ou `gho_...`) estiver presente no contexto do erro
- **THEN** o token é substituído por `[TOKEN_OCULTADO]` antes do envio.
