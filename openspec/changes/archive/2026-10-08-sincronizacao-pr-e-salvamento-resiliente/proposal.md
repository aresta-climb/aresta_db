# Proposal

## Why

Atualmente, o editor impede o salvamento regular e a publicação ou atualização de Pull Requests quando a compilação local de um croqui falha. Isso cria uma barreira crítica para novos colaboradores e usuários, impedindo que pessoas peçam ajuda à comunidade enviando propostas de mudança que necessitam de correções colaborativas. Além disso, a sincronização de Pull Requests é estritamente unidirecional (local para remoto), sem mecanismo para puxar alterações feitas diretamente no GitHub ou por mantenedores, nem conciliar divergências históricas via Git.

Esta mudança desacopla o salvamento físico dos dados das falhas de compilação, permite a abertura e atualização de Pull Requests com croquis não-compilando mediante confirmação, e implementa a sincronização bidirecional entre o editor local e a branch remota da PR com resolução de conflitos preservada no histórico do Git.

## What Changes

- **Salvamento Resiliente**: O salvamento no disco (`croqui.yaml` e arquivos de dados) é concluído com sucesso e o estado é marcado como limpo (`setClean()`), independentemente do resultado da compilação.
- **Exibição Não-Bloqueante de Erros de Compilação**: Erros ou avisos decorrentes de compilação/deploy não disparam diálogos modais de erro crítico (`DialogoErroSalvamento`), sendo direcionados exclusivamente para o painel inferior (`WidgetSaidaCompilacao`).
- **Envio de PR com Confirmação para Croquis com Erro**: A validação pré-publicação deixa de barrar terminantemente o envio quando há erros de compilação, passando a solicitar confirmação explícita do usuário para prosseguir.
- **Botão de Sincronização na Barra Superior**: Adição de uma ação de sincronização à direita do botão "Propor Mudança", habilitada quando o croqui experimental possuir uma Pull Request ativa no GitHub.
- **Sincronização Bidirecional da PR**: Capacidade de buscar (`fetch`) e mesclar (`merge`) alterações da branch remota da PR ao abrir o croqui, antes de publicar ou sob demanda pelo botão da barra superior.
- **Resolução de Conflitos Preservada no Git**: Diálogo simples de decisão ("Manter Minha Versão Local" vs "Usar Versão do GitHub") que executa um commit de merge com dois pais (`parents`), garantindo preservação de todo o histórico no grafo do Git sem deixar marcadores de conflito em arquivos.

## Capabilities

### New Capabilities
- `sincronizacao-remota-pr`: Sincronização bidirecional entre a pasta de trabalho do croqui experimental e a branch remota da Pull Request no GitHub, incluindo detecção de novidades remotas, tentativa de merge automático e resolução de conflitos gerando commits de merge com duplo parentesco.

### Modified Capabilities
- `salvamento-assincrono`: O salvamento em background conclui a gravação em disco com sucesso mesmo quando o deploy/compilação reportar erros, canalizando as mensagens para o log de compilação sem disparar diálogos de falha de I/O.
- `editor-submissao-sugestoes`: A validação pré-envio de publicação passa a permitir a criação ou atualização de Pull Requests contendo erros de compilação mediante confirmação do usuário.

## Impact

- `editor/core/worker.py`: Ajustes na `TarefaSalvamento` para não emitir `erro` quando o deploy falhar por validação de croqui, e criação da `TarefaSincronizacaoPR`.
- `editor/core/workspace.py`: Tratamento de exceções de compilação para retornar mensagens de erro sem propagar `RuntimeError` para fora de `processar_renomeacao_e_compilacao`.
- `editor/controllers/publish_controller.py`: Modificação de `_validar_compilacao_limpa` para suportar confirmação do usuário (`QMessageBox.question` ou diálogo explicativo) e integração da sincronização prévia.
- `editor/legacy_views/area_principal.py`: Inclusão do botão `acao_sincronizar` na barra de ferramentas superior, acionamento ao abrir croqui e roteamento de conflitos.
- `editor/core/servico_submissao.py` e `editor/core/sync.py`: Operações de fetch da branch de PR e rotina de merge/reconciliação via `pygit2`.
