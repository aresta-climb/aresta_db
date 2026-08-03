## Why

O fluxo atual de criação de Pull Requests no Editor Aresta apresenta erros (como HTTP 500 no GitHub) devido a problemas com o mapeamento de permissões e tentativas de push direto no repositório base. Além disso, a implementação atual em `legacy_views/area_principal.py` é bloqueante de forma incorreta e não segue um padrão de separação de responsabilidades (MVC). Implementar este fluxo corretamente é o passo final crítico para fechar o ciclo de desenvolvimento do editor. 

Adicionalmente, esta refatoração tem o objetivo explícito de alinhar o código com os **Princípios Inegociáveis de Desenvolvimento** (PRINCIPIOS.md), aplicando TDD (Test-Driven Development), focando primeiramente em testes de integração, assegurando 100% de cobertura de testes unitários para a nova lógica, além de padronizar a documentação (docstrings) inteiramente em português.

## What Changes

- Implementação do botão e rotina de criação de Pull Request baseada exclusivamente no uso de "Forks", garantindo estabilidade de permissões.
- Reestruturação do código para o padrão MVC, extraindo a lógica da interface do usuário para um `PublishController` e a view para um `PublishDialog`.
- Uso do diálogo de espera já existente (`_mostrar_modal_fechamento`) de forma genérica para bloquear a tela durante o salvamento inicial do croqui, antes de iniciar o fluxo de publicação.
- Delegação da compilação do `.croqui` (para download e teste pelos revisores) a um bot de CI/CD (GitHub Actions) em vez de rodar `deploy_generated.py` no cliente.
- Atualização silenciosa de Pull Requests existentes se o usuário clicar novamente em publicar, após avisar se o PR antigo já foi fechado/mergeado.
- Adição de informações de rastreamento de PR (`pull_request_url`, `pull_request_branch`, `pull_request_fork_owner`) ao protobuf do `CroquiExperimental`.
- **Adoção Estrita do TDD e Cobertura**: Toda a lógica MVC e do worker será criada seguindo o ciclo Red-Green-Refactor, garantindo que os testes de integração e unitários pautem o desenvolvimento e cheguem a 100% de cobertura no novo código.

## Capabilities

### New Capabilities
- `github-publish-flow`: Coordena a sincronização Git do repositório usando um modelo baseado em fork, o controle de UI para o diálogo de Pull Request, e o tracking da branch criada para futuras atualizações.

### Modified Capabilities
- Nenhuma. (Requisitos das outras partes se mantêm iguais).

## Impact

- Modificação nas definições do Protobuf (`aresta_api/proto/croqui_experimental.proto`).
- Refatoração extensa na classe `JanelaPrincipal` em `editor/legacy_views/area_principal.py` para remoção do código legado.
- Criação de novos arquivos no editor: `editor/controllers/publish_controller.py` e `editor/views/publish_dialog.py`.
- Alteração profunda no script de sincronização com o Git (`editor/core/sync.py`) e na thread de publicação (`editor/core/worker.py`).
- Implementação massiva de testes em `tests/editor/controllers/` e `tests/editor/core/` para suportar o fluxo TDD estabelecido.
