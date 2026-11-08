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
O serviço `git-proxy` MUST validar se uma nova branch sendo criada já existe no repositório remoto oficial antes de encaminhar o tráfego e garantir que registros na tabela de controle `sugestoes_branches` reflitam apenas branches efetivamente criadas no GitHub.

#### Scenario: Criação de Nova Branch Inexistente Confirmada no GitHub
- **WHEN** o push possuir `old_oid` igual a `0000000000000000000000000000000000000000`, a branch não existir no GitHub e o `git-receive-pack` efetivar a referência sem erros (`ok refs/heads/...`)
- **THEN** o serviço MUST manter o vínculo entre a branch, o identificador do usuário, o e-mail do autor e o nome do autor na tabela `sugestoes_branches`

#### Scenario: Rollback de Registro quando o Push Falha em Criar a Branch
- **WHEN** o push possuir `old_oid` nulo mas o `git-receive-pack` do GitHub falhar (status HTTP de erro ou recusa `ng refs/heads/...` / `unpack error` no stream `pkt-line`)
- **THEN** o serviço MUST remover ou abster-se de persistir o registro da branch na tabela `sugestoes_branches`, evitando bloqueios por conflito `409` em tentativas subsequentes

#### Scenario: Tentativa de Criação com Nome em Conflito
- **WHEN** o push possuir `old_oid` nulo mas a branch já existir no GitHub ou na tabela de controle
- **THEN** o serviço MUST rejeitar o push com erro HTTP 409 Conflict

### Requirement: Verificação de Propriedade em Atualizações de Branch
O serviço `git-proxy` MUST garantir que apenas o autor original de uma sugestão possa enviar novos commits para a mesma branch.

#### Scenario: Atualização pelo Autor Original
- **WHEN** o push for uma atualização (`old_oid` não nulo) em uma branch existente e o e-mail autenticado for idêntico ao e-mail do criador registrado
- **THEN** o serviço MUST autorizar e encaminhar a atualização

#### Scenario: Tentativa de Atualização por Usuário Distinto
- **WHEN** o push for uma atualização em uma branch existente e o e-mail autenticado for diferente do autor original
- **THEN** o serviço MUST rejeitar o push com HTTP 403 Forbidden indicando que a sugestão pertence a outro autor

### Requirement: Streaming Seguro e Injeção de Credenciais para o GitHub
O serviço `git-proxy` MUST injetar as credenciais seguras do Bot do GitHub, encaminhar o tráfego Git Smart HTTP e inspecionar o resultado do `git-receive-pack` para reportar falhas de protocolo ao Sentry.

#### Scenario: Encaminhamento de Tráfego Válido
- **WHEN** todas as validações de firewall e propriedade forem satisfeitas
- **THEN** o serviço MUST repassar a requisição para `https://github.com/aresta-climb/aresta_db.git` autenticando com o Token do Bot e devolvendo a resposta `pkt-line` intacta ao cliente

#### Scenario: Telemetria de Rejeição de Referência no git-receive-pack
- **WHEN** o GitHub retornar resposta de `git-receive-pack` contendo erro de desempacotamento (`unpack`) ou recusa de referência (`ng refs/heads/<branch> <motivo>`)
- **THEN** o serviço `git-proxy` MUST capturar e reportar o erro ao Sentry com a tag `etapa="git_receive_pack_ref"` e os detalhes da branch e motivo da rejeição
