## Context
O editor foi originalmente estruturado ao redor do ciclo de vida de "Croquis Experimentais". Essa estrutura exige um diretório com formato `.croqui` extraído, o qual contém sua própria árvore de pastas fixa (com as pastas filhas `database` e `compilado`) e gerencia a criação de um repositório git local temporário onde são commitadas todas as alterações via `GerenciadorCroquiExperimental`.
Para usuários com o ambiente de desenvolvimento completo (`aresta_db`) configurado e clonado na máquina local, o formato experimental é contra-produtivo e excessivamente complexo. Eles preferem operar sobre os diretórios já existentes: alterar em `database/<id>` e compilar em `generated/<id>`.

## Goals / Non-Goals

**Goals:**
- Permitir carregar croquis contidos diretamente no clone do repositório `aresta_db`.
- Isolar as regras de persistência (git, pastas de build, renomeação) da Interface do Usuário (`JanelaPrincipal`).
- Adaptar as lógicas do editor para respeitarem as práticas do Git padrão quando o croqui estiver diretamente no repositório.

**Non-Goals:**
- Não removeremos ou desativaremos o fluxo de "Croquis Experimentais", pois ele continua útil para usuários não técnicos.
- Não faremos refatorações extremas na API local de dados (modelos e controllers continuarão recebendo Paths base para operar).

## Decisions

- **Interface `Workspace`**: Criação de uma abstração base `EditorWorkspace` que terá implementações de `ExperimentalWorkspace` e `LocalRepoWorkspace`. Essa interface proverá métodos `get_database_path()`, `get_compilado_path()` e `salvar_croqui(janela)`.
- **Detecção Automática do Modo no Startup**: No `main.py`, se o `sys.argv[1]` referenciar um diretório existente (ex: `database/arcos_corumba` que possua `croqui.yaml`), instancia-se `LocalRepoWorkspace` e o sistema abre diretamente a `JanelaPrincipal`, pulando o Auth Controller e o Worker do Github.
- **Renomeação usando `git mv` no modo Local**: No modo LocalRepo, se o ID for modificado, `workspace.salvar_croqui()` executará a movimentação dos diretórios `database/<id>` e `generated/<id>` via `git mv` para não perder o tracking.
- **Modificações de UI no modo Local**: No `LocalRepoWorkspace`, um flag indicará a indisponibilidade de publicar diretamente (`can_publish_pr = False`). A UI (`JanelaPrincipal`) deixará o botão "Publicar" visível porém desabilitado (cinza). Além disso, o título da janela passará a exibir explicitamente a tag `[Local Mode]` para evitar confusões.
- **Test-Driven Development (TDD)**: O desenvolvimento das lógicas do Workspace e das abstrações DEVE acontecer estritamente usando TDD, criando a suíte de testes (`_test.py`) com 100% de coverage para garantir que não haja regressões, conforme diretrizes do `PRINCIPIOS.md`.

## Risks / Trade-offs

- **Falha de sincronização na renomeação do ID no modo Local** -> Mitigação: Se o `git mv` falhar (por exemplo, se existirem modificações no index conflitantes ou se o comando não for encontrado), trataremos o erro de modo elegante exibindo uma mensagem ao usuário e abortando a mudança de ID no YAML, para evitar descompasso entre o ID e a pasta no repositório.
