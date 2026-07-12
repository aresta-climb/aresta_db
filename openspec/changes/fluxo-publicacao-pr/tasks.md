## 1. Protobuf e Metadados

- [x] 1.1 Adicionar campos de PR (`pull_request_url`, `pull_request_branch`, `pull_request_fork_owner`) em `aresta_api/proto/croqui_experimental.proto` mantendo nomes em português e documentação via docstrings no estilo Protobuf.
- [x] 1.2 Rodar o script de build de protos para gerar os arquivos `_pb2.py`.

## 2. Testes de Integração e Unidade (TDD First)

- [x] 2.1 Criar suite de testes de integração (`tests/editor/controllers/publish_controller_test.py`) focada em testar os contratos de estado: bloqueio de interface, acionamento do worker e interações entre `PublishController`, `PublishDialog` e repositório.
- [x] 2.2 Criar suite de testes unitários (`tests/editor/core/sync_test.py` e `tests/editor/core/worker_test.py`) mockando a API do Github e PyGit2 para garantir cobertura 100% dos novos métodos criados em `sync.py` e `worker.py` (fluxo de nova PR e atualização de PR).

## 3. Implementação MVC (Green Phase)

- [x] 3.1 Criar `editor/views/publish_dialog.py` com documentação (docstrings em Português) e limpar a lógica correspondente de `area_principal.py`.
- [x] 3.2 Criar `editor/controllers/publish_controller.py` com docstrings detalhando o fluxo MVC e garantir que passe nos testes escritos no passo 2.1.
- [x] 3.3 Refatorar `_mostrar_modal_fechamento` em `area_principal.py` para um método reutilizável (`_mostrar_modal_espera`) sem abstrações desnecessárias.
- [x] 3.4 Integrar o `PublishController` em `area_principal.py` e validar a integração.

## 4. Sincronização e Worker (Refactoring)

- [x] 4.1 Atualizar `editor/core/sync.py` com docstrings claras, garantindo a criação do remote `upstream` e forçando o uso do Fork como `origin`. Validar se passa nos testes unitários (100% de coverage para esta mudança).
- [x] 4.2 Refatorar `TarefaInicializacao` (`editor/core/worker.py`) para realizar o `fetch` de `origin` e `upstream`, fazendo checkout de `upstream/main`. Garantir simplicidade na implementação sem excesso de abstração.
- [x] 4.3 Refatorar `TarefaPublicacao` para lidar com as lógicas de Push, mantendo os testes unitários passando. Implementar a checagem de modificações pendentes no Git, commit, e push padrão para `origin`.
- [x] 4.4 Na `TarefaPublicacao`, usar a API do GitHub para criar a PR baseada no `head=owner:branch` ou atualizar os metadados silenciosamente.
- [x] 4.5 Salvar as alterações no croqui (protobuf) local de forma imediata após o sucesso da `TarefaPublicacao`.
- [x] 4.6 Rodar suite de testes completa e garantir que toda a cobertura de teste das modificações efetuadas está em 100%.
