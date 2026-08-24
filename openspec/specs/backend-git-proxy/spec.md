## ADDED Requirements

### Requirement: Autenticação de Requisições Git via JWT e Metadados do Autor
O serviço `git-proxy` MUST validar o cabeçalho de autenticação (`Authorization: Bearer <JWT>`) contra o serviço Supabase Auth antes de processar qualquer tráfego Git, recuperando a identidade do autor (e-mail e nome completo).

#### Scenario: Requisição com Token Válido e Metadados
- **WHEN** o cliente Git enviar requisição `GET /info/refs?service=git-receive-pack` ou `POST /git-receive-pack` contendo JWT válido
- **THEN** o serviço MUST extrair o identificador (`user_id`), o e-mail verificado e o nome do autor (`nome_completo` dos metadados do usuário) e permitir o prosseguimento da análise

#### Scenario: Requisição sem Token ou Token Inválido
- **WHEN** a requisição Git não contiver cabeçalho `Authorization` ou o JWT for inválido/expirado
- **THEN** o serviço MUST interromper o fluxo e retornar HTTP 401 Unauthorized

### Requirement: Firewall de Nomes de Branch
O serviço `git-proxy` MUST inspecionar os primeiros bytes do payload do comando Git (`pkt-line`) para assegurar que a branch de destino obedece à regra de nomenclatura de sugestões.

#### Scenario: Push para Branch de Sugestão Válida
- **WHEN** o comando Git contiver uma referência de destino casando com a expressão regular `^refs/heads/sugestao-[a-zA-Z0-9_-]+$`
- **THEN** o serviço MUST permitir a continuidade do processamento

#### Scenario: Push para Branch Inválida ou Principal
- **WHEN** o comando Git contiver referência para `refs/heads/main` ou qualquer padrão fora de `sugestao-*`
- **THEN** o serviço MUST rejeitar a operação retornando HTTP 403 Forbidden com mensagem de erro explicativa no protocolo Git

### Requirement: Prevenção de Conflito em Novas Branches
O serviço `git-proxy` MUST validar se uma nova branch sendo criada já existe no repositório remoto oficial antes de encaminhar o tráfego.

#### Scenario: Criação de Nova Branch Inexistente
- **WHEN** o push possuir `old_oid` igual a `0000000000000000000000000000000000000000` e a branch não existir no GitHub
- **THEN** o serviço MUST registrar o vínculo entre a branch, o e-mail do autor e o nome do autor na tabela de controle e prosseguir com o push

#### Scenario: Tentativa de Criação com Nome em Conflito
- **WHEN** o push possuir `old_oid` nulo mas a branch já existir no GitHub ou na tabela de controle
- **THEN** o serviço MUST rejeitar o push com erro HTTP 409 Conflict ou mensagem de rejeição no stream Git

### Requirement: Verificação de Propriedade em Atualizações de Branch
O serviço `git-proxy` MUST garantir que apenas o autor original de uma sugestão possa enviar novos commits para a mesma branch.

#### Scenario: Atualização pelo Autor Original
- **WHEN** o push for uma atualização (`old_oid` não nulo) em uma branch existente e o e-mail autenticado for idêntico ao e-mail do criador registrado
- **THEN** o serviço MUST autorizar e encaminhar a atualização

#### Scenario: Tentativa de Atualização por Usuário Distinto
- **WHEN** o push for uma atualização em uma branch existente e o e-mail autenticado for diferente do autor original
- **THEN** o serviço MUST rejeitar o push com HTTP 403 Forbidden indicando que a sugestão pertence a outro autor

### Requirement: Streaming Seguro e Injeção de Credenciais para o GitHub
O serviço `git-proxy` MUST injetar as credenciais seguras do Bot do GitHub e fazer o streaming bidirecional do tráfego Git Smart HTTP em tempo real.

#### Scenario: Encaminhamento de Tráfego Válido
- **WHEN** todas as validações de firewall e propriedade forem satisfeitas
- **THEN** o serviço MUST repassar a requisição via stream para `https://github.com/aresta-climb/aresta_db.git` autenticando com o Token do Bot e devolvendo a resposta intacta ao cliente
