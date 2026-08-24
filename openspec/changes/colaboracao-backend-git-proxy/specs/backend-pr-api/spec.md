## ADDED Requirements

### Requirement: Autenticação e Recepção de Dados de PR
O endpoint REST `create-pr` MUST validar a identidade do requisitante via JWT do Supabase e aceitar os parâmetros da sugestão com nome e e-mail do autor.

#### Scenario: Chamada Autenticada com Sucesso
- **WHEN** o cliente enviar uma requisição `POST /create-pr` com JWT válido e payload contendo `branch`, `title`, `description` e metadados do autor (`author_name`, `author_email`)
- **THEN** o serviço MUST iniciar o fluxo de validação e abertura de PR

#### Scenario: Chamada com Credenciais Inválidas
- **WHEN** o endpoint `POST /create-pr` for invocado sem JWT ou com token expirado
- **THEN** o serviço MUST retornar HTTP 401 Unauthorized

### Requirement: Validação de Escopo de Pastas Restritas
O serviço `create-pr` MUST inspecionar a lista de arquivos modificados na branch da sugestão antes de formalizar a Pull Request.

#### Scenario: Alterações Exclusivas em database/
- **WHEN** todos os arquivos alterados na branch `sugestao-*` pertencerem exclusivamente ao caminho `database/`
- **THEN** o serviço MUST prosseguir para a criação do Pull Request

#### Scenario: Tentativa de Modificação Fora de database/
- **WHEN** a branch `sugestao-*` contiver alterações em arquivos fora de `database/` (ex: workflows, código-fonte ou raiz)
- **THEN** o serviço MUST deletar a branch remota no GitHub e responder com HTTP 400 Bad Request descrevendo a violação de segurança

### Requirement: Abertura Automatizada de Pull Request com Atribuição ao Autor
O serviço `create-pr` MUST abrir a Pull Request no repositório `aresta-climb/aresta_db` utilizando a API do GitHub com o token do Bot, formatando a descrição com o nome e e-mail do autor.

#### Scenario: Criação de Novo Pull Request Formatado
- **WHEN** a validação de diretório for aprovada e não houver PR aberta para a branch
- **THEN** o serviço MUST criar o Pull Request apontando da branch de sugestão para `main`, formatando o título e corpo com o nome completo e e-mail do autor e retornando a URL do PR criado

#### Scenario: Atualização de Registro de PR
- **WHEN** o Pull Request for criado com sucesso no GitHub
- **THEN** o serviço MUST registrar o número e URL do PR na tabela de controle `sugestoes_branches`
