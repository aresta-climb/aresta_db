## Context

O Aresta Editor permite que usuários criem e editem croquis ("croquis experimentais") localmente e os enviem ao repositório principal `aresta-climb/aresta_db` via Pull Request. A implementação original tinha falhas de separação de responsabilidades (MVC) e de permissões de Git/GitHub (tentava interagir com o repositório base independentemente do usuário ter um fork ou não). Adicionalmente, estamos adequando o fluxo aos **Princípios Inegociáveis de Desenvolvimento** para garantir TDD e cobertura 100%.

## Goals / Non-Goals

**Goals:**
- Implementar o padrão MVC para o fluxo de Publicação (PublishController, PublishDialog).
- Garantir que a via de publicação e sincronização seja **sempre** o Fork do usuário, simplificando as permissões e evitando o erro HTTP 500 no `create_pull`.
- Utilizar a API PyGit2 e o GitHub API de maneira idempotente para o croqui atual, tratando re-envios de PRs existentes de forma silenciosa e transparente.
- Mapear a PR criada aos dados do protobuf local para tracking contínuo.
- **Atingir 100% de Unit Test Coverage**: Seguir o TDD (Red-Green-Refactor) testando integrações antes de implementações concretas e mantendo documentação puramente em português.

**Non-Goals:**
- Não executaremos o empacotamento (`deploy_generated.py` -> `.croqui`) localmente para submissão; isso será responsabilidade do CI via GitHub Actions para evitar complexidade e lixo no PR.
- Não faremos resolução de conflito de merge complexa no lado do cliente: a pasta `database/{id}` local do croqui é sempre considerada soberana e vai sobrescrever o remote via `push` padrão no fork.

## Decisions

### 1. Uso Exclusivo de Fork
*Rationale*: O Github lida muito melhor com forks para criação de PRs comunitários. Mesmo para usuários com permissão de escrita, ter uma lógica uniforme baseada em forks garante que o Pull Request sempre tem um head do tipo `owner:branch`.
*Implementação*: 
- Na inicialização, garantimos que clonamos o Fork do usuário (e criamos se necessário).
- O remote `origin` apontará para o Fork. O remote `upstream` apontará para `aresta-climb/aresta_db`.
- O checkout e o push são sempre no `origin`.

### 2. Estratégia de Testes (TDD e Integração Primeiro)
*Rationale*: Evitar regressões na sincronização com Github (que já apresentou problemas no passado) e obedecer ao `PRINCIPIOS.md`.
*Implementação*:
- A suíte de testes de integração deve ser criada **antes** da implementação real de `PublishController`. Usaremos mocks para o comportamento do Github API. 
- Somente após os testes indicarem os contratos corretos as classes reais serão preenchidas.
- Nenhuma abstração desnecessária ou "Factory" genérica deve ser criada, mantendo o código simples, legível e testável.

### 3. Bloqueio Seguro Durante o Salvamento
*Rationale*: O `salvar_croqui()` em `area_principal.py` inicia um worker (assíncrono). Prosseguir para a tela do PR imediatamente causava concorrência de I/O.
*Implementação*: O `PublishController` instanciará a mesma barra de progresso modal sem botão de cancelar (`_mostrar_modal_fechamento`) antes de prosseguir com as requisições, ouvindo o sinal de `sucesso` do salvamento.

### 4. Tracking da Branch no Protobuf
*Rationale*: Saber se o usuário já tem uma PR aberta evita duplicação ou o uso de botões errados no GitHub.
*Implementação*: Salvaremos `pull_request_branch`, `pull_request_url` e `pull_request_fork_owner` no arquivo `.yaml` de metadados do croqui (que preenche o proto `CroquiExperimental`). O controller lerá isso para decidir o fluxo.

## Risks / Trade-offs

- **Push para Branch Fechada/Mergeada**: Se a branch existir no fork mas a PR original já foi mergeada no base, fazer push para ela pode poluir ou causar comportamentos bizarros na aba de PRs do Github.
  *Mitigação*: Antes de um push, usaremos a API do GitHub para checar o estado da PR. Se estiver fechada/mergeada, avisaremos o usuário e recomeçaremos uma branch/PR limpa.

- **Falta do arquivo .croqui na Pull Request**: Sem gerar localmente, o avaliador no Github não pode baixar o arquivo instantaneamente.
  *Mitigação*: Devemos contar com o Github Actions CI para postar o compilado no PR como comentário ou artifact, o que é mais sustentável.
