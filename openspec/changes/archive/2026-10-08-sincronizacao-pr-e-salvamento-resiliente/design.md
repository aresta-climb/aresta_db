# Design

## Context

Atualmente, o editor falha ao salvar dados caso a compilação encontre qualquer erro no croqui, pois `deploy()` em [`scripts/deploy_generated.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/scripts/deploy_generated.py#L1036) levanta `RuntimeError`, o qual não é contido por [`ExperimentalWorkspace`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/workspace.py#L97-L116) e faz a [`TarefaSalvamento`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/worker.py#L309-L370) disparar um erro crítico modal (`DialogoErroSalvamento`). Com isso, a interface não marca a pilha como limpa (`setClean()`), passa a falsa impressão de que os dados não foram gravados no disco e impede que as mensagens cheguem ao [`WidgetSaidaCompilacao`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/widget_saida_compilacao.py) inferior.

Além disso, em [`PublishController`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/controllers/publish_controller.py#L138-L161), a validação pré-publicação bloqueia completamente o envio se houver erros de compilação, impossibilitando que colaboradores compartilhem seus esboços e peçam auxílio remoto. Por fim, a sincronização é unidirecional (apenas push local para remoto), sem mecanismo para trazer de volta à pasta de trabalho commits adicionados na Pull Request no GitHub.

## Goals / Non-Goals

**Goals:**
- Desacoplar a gravação física dos dados das falhas de compilação: salvar sempre grava `croqui.yaml` e arquivos anexos com sucesso, limpa a pilha de histórico e exibe mensagens de erro/aviso de compilação exclusivamente no painel inferior.
- Substituir o bloqueio rígido de envio de Pull Request por um diálogo de confirmação explicativo, permitindo publicar propostas contendo erros de compilação.
- Implementar sincronização bidirecional entre o editor e a branch remota da PR vinculada (ao carregar o croqui, antes de publicar e através de botão explícito na barra superior).
- Implementar reconciliação de conflitos através de commit de merge com dois pais (`parents`) no Git, suportando as decisões "Manter Minha Versão Local" e "Usar Versão do GitHub", garantindo preservação integral do histórico e integridade do YAML.

**Non-Goals:**
- Não criar interface complexa de 3-way merge ou visualizador gráfico side-by-side de diffs (manter a simplicidade com decisão binária local/remoto).
- Não implementar listagem e importação de PRs remotas na `TelaDeCarregamento` nesta iteração (fica reservado para alteração futura).
- Não alterar a esteira de CI/CD do GitHub Actions (as verificações de qualidade e bloqueio de merge acidental na `main` continuam vigentes no repositório remoto).

## Decisions

### Decisão 1: Captura e contenção de exceções de compilação no Workspace
- **Decisão**: Em `ExperimentalWorkspace.processar_renomeacao_e_compilacao` (e de forma análoga no `LocalRepoWorkspace`), envolver a chamada `gerenciador.compilar_croqui(caminho)` em bloco de captura para que exceções de compilação (`RuntimeError`) não vazem como falhas de execução. As mensagens de log capturadas do `deploy()` serão extraídas e retornadas normalmente na tupla `(caminho, mensagens, database_modificado)`.
- **Alternativas consideradas**:
  - *Fazer o `deploy()` nunca lançar exceções*: Descartado porque o script `deploy_generated.py` também é usado no CI/CD e em linha de comando, onde pode ser desejável falhar caso chamado com outras flags.
  - *Capturar na `TarefaSalvamento`*: Tratar no workspace é mais limpo e centralizado, pois o workspace é o responsável pelo contrato de compilação com a UI.

### Decisão 2: Confirmação não-bloqueante no PublishController
- **Decisão**: Em `PublishController._validar_compilacao_limpa`, se `erros` estiver presente, exibir um `QMessageBox.question` em vez de `QMessageBox.critical`. O texto informará que o croqui possui erros de compilação e perguntará se o usuário deseja submetê-lo assim mesmo para revisão colaborativa. Se o usuário responder afirmativamente, o método retorna `True` e prossegue com o envio.
- **Alternativas consideradas**:
  - *Enviar silenciosamente sem perguntar*: Descartado porque o usuário pode não ter percebido que o croqui continha erros antes de publicar.

### Decisão 3: Mecânica de Sincronização Remota via pygit2 no ServicoSubmissao
- **Decisão**: Criar o método `sincronizar_com_pr_remota` no `ServicoSubmissao` (e tarefa assíncrona `TarefaSincronizacaoPR` em `worker.py`):
  1. Realiza `fetch` da branch remota da PR a partir do remote público (`origin` ou `proxy`).
  2. Verifica se a branch remota possui commits novos em relação à branch local.
  3. Tenta a mesclagem automática de 3 vias (`pygit2.Repository.merge_trees`).
  4. Se não houver conflitos: grava o commit de merge, copia os arquivos atualizados para a pasta `database/` do croqui experimental e recarrega os dados na interface.
  5. Se houver conflitos: aborta a escrita imediata e retorna sinal de conflito para a UI exibir o diálogo de escolha.
- **Alternativas consideradas**:
  - *Usar Git CLI via subprocess*: Descartado para manter conformidade estrita com o princípio de portabilidade sem depender do binário `git` no PATH do Windows/macOS.

### Decisão 4: Resolução de Conflitos Preservando Histórico Git
- **Decisão**: Quando o usuário optar por "Manter Minha Versão Local" ou "Usar Versão do GitHub", o sistema resolve o índice conflitante (`index.conflicts`) selecionando a árvore correspondente (*ours* ou *theirs*), grava o índice e cria um commit de merge com dois pais (`[local_commit_oid, remote_commit_oid]`).
- **Por que isso é superior**:
  - Ambas as ramificações permanecem íntegras no histórico do Git.
  - A Pull Request no GitHub reflete a resolução claramente na timeline.
  - Não são gerados arquivos temporários `.bak` que poluem o sistema de arquivos sem mecanismo de restauração.

### Decisão 5: Botão Contextual na Barra Superior
- **Decisão**: Adicionar `acao_sincronizar` à direita de `acao_publicar` na `toolbar_superior` de [`JanelaPrincipal`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/legacy_views/area_principal.py).
  - Ícone: `sincronizar` (setas circulares de reload).
  - Desabilitada no `Local Mode` ou quando o croqui não tiver PR aberta.
  - Habilitada quando `pull_request_branch` estiver presente no `croqui_experimental.yaml`.

## Risks / Trade-offs

- **[Risco] Falha de conexão de rede durante o fetch da sincronização**  
  → **Mitigação**: O `fetch` remoto é encapsulado em tratamento de exceções de rede. Se falhar por timeout ou ausência de internet, a interface emite notificação informativa toast sem interromper a sessão local nem travar o editor.

- **[Risco] Conflito em imagens binárias**  
  → **Mitigação**: Arquivos binários não aceitam mesclagem linha a linha. A resolução de conflito escolhendo a versão local ou remota resolve integralmente tanto arquivos de texto (`croqui.yaml`, `.md`) quanto imagens (`.jpg`, `.png`).

- **[Risco] Recarregamento dos dados na UI perder o foco ou o nó selecionado**  
  → **Mitigação**: Reutilizar a rotina existente `_recarregar_dados_apos_salvamento()` que já preserva o nó selecionado na árvore de navegação antes de recarregar os dados do disco.
