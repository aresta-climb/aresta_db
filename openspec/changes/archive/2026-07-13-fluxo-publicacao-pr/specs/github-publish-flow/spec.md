## ADDED Requirements

### Requirement: Integração Segura baseada em Fork
O sistema MUST realizar o envio das edições de croqui obrigatoriamente através de um fork do repositório base (`aresta-climb/aresta_db`) na conta do usuário autenticado.

#### Scenario: Repositório recém inicializado
- **WHEN** a `TarefaInicializacao` sincroniza os repositórios
- **THEN** o sistema configura o fork do usuário como o remote `origin` e o repositório base como `upstream`, fazendo `fetch` em ambos.

### Requirement: Bloqueio Seguro no Salvamento
O sistema SHALL exibir um diálogo modal bloqueante quando um croqui com alterações não salvas precisa ser salvo antes de abrir a janela de Publicação.

#### Scenario: Usuário tenta publicar croqui com modificações pendentes
- **WHEN** o usuário clica em Publicar
- **THEN** o sistema pergunta se deseja salvar. Se sim, exibe um diálogo "Salvando croqui..." e aguarda a finalização de `TarefaSalvamento` antes de prosseguir.

### Requirement: Detecção de PR Existente e Atualização
O sistema SHALL detectar no protobuf `CroquiExperimental` se uma branch e uma Pull Request já foram criadas para o croqui atual, avisando o usuário se ela foi fechada/mergeada ou atualizando silenciosamente se estiver aberta.

#### Scenario: Atualização de PR existente
- **WHEN** o usuário publica um croqui que já possui `pull_request_branch` salvo no proto
- **THEN** o sistema não pede título/descrição novamente, faz o checkout da branch existente do remote `origin`, sobrescreve a pasta database, commita e faz push.

#### Scenario: PR antigo já foi fechado ou mergeado
- **WHEN** o sistema detecta a `pull_request_branch` mas a PR na API do GitHub não está mais aberta
- **THEN** o sistema avisa o usuário e cria uma nova branch/PR limpa, esquecendo os dados da PR antiga.

### Requirement: Abortar publicação se não houver modificações
O sistema MUST abortar o processo de push caso, após copiar a pasta `database/{id}` para o repositório local, a árvore do Git não apresente nenhuma mudança a ser commitada.

#### Scenario: Publicação redundante
- **WHEN** o usuário clica em Publicar sem ter feito modificações novas na pasta do croqui
- **THEN** a rotina identifica a ausência de diff e informa o usuário que "Nenhuma mudança nova identificada em relação ao projeto base".
