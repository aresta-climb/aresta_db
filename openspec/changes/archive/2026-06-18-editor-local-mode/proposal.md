## Why

Atualmente, o editor Desktop foi projetado exclusivamente para operar com o fluxo de "Croquis Experimentais" (arquivos `.croqui` extraídos e controlados via git localmente). Isso gera atrito para usuários que já possuem o repositório principal `aresta_db` clonado e desejam editar e compilar croquis oficiais diretamente na sua máquina local de forma ágil, sem os overheads de sincronização e autenticação do GitHub. Este modo local irá acelerar o fluxo de edição e revisão de croquis do repositório.

## What Changes

- Introdução do conceito de `Workspace` no aplicativo com suporte a dois modos: `WorkspaceExperimental` e `WorkspaceLocalRepo`.
- O modo `WorkspaceLocalRepo` (Repositório Local) será ativado automaticamente ao iniciar o editor via linha de comando passando a pasta do croqui dentro de `database/` (ex: `python editor/main.py database/<croqui>`).
- No modo Local, a inicialização pulará as etapas de autenticação no GitHub e sincronização.
- Durante o salvamento no modo Local, o editor não utilizará o `GerenciadorCroquiExperimental` para commitar no git e vai compilar a saída diretamente para a pasta `generated/<croqui>`.
- Renomeação de ID na UI no modo Local renomeará a pasta no repositório mantendo o tracking do git via `git mv` nas pastas `database/` e `generated/`.
- O botão "Publicar" será desabilitado (cinza na UI) durante o uso do modo Local, já que o usuário deve gerenciar os commits e PRs nativamente através do seu terminal/VSCode.
- A Interface do Usuário (na barra superior ou no título da janela) exibirá de forma clara que o aplicativo está rodando em "Local Mode".

## Capabilities

### New Capabilities
- `editor-local-mode`: Operação nativa do editor diretamente no repositório `aresta_db`, sem uso de arquivos experimentais.
- `workspace-interface`: Abstração de caminhos e ações de persistência do croqui (Experimental vs. Local Repo).

### Modified Capabilities


## Impact

- `editor.main`: Bypass das telas de autenticação e carregamento.
- `editor.legacy_views.area_principal` (JanelaPrincipal): Remoção de hardcodes de caminhos (`database/`, `compilado/`) em favor do uso da interface do Workspace ativo; alteração na lógica do botão de publicação e salvamento.
- Desacoplamento do salvamento de arquivos das operações de controle de versão (Git) do `GerenciadorCroquiExperimental`.

## Engineering Principles

- **TDD (Test-Driven Development)**: Todo código novo ou refatorado (`workspace.py`, etc) seguirá um fluxo rigoroso de TDD. Os testes (`_test.py`) devem ser escritos e falhar antes da implementação do código funcional.
- **Test Coverage**: A implementação desta proposta garante **100% de unit test coverage** para qualquer lógica nova adicionada ou modificada de acordo com o `PRINCIPIOS.md`.
