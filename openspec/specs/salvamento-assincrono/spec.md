## ADDED Requirements

### Requirement: Salvamento de croqui não bloqueante
O sistema SHALL executar as rotinas de persistência do croqui (disco/banco de dados) em uma thread separada (background), evitando qualquer congelamento da interface principal.

#### Scenario: Iniciando salvamento
- **WHEN** o usuário aciona a ação de "Salvar" (via botão ou atalho de teclado)
- **THEN** o sistema extrai um *snapshot* imutável do estado atual dos dados na memória principal (Main Thread), exibe o indicador "Salvando..." na UI, delega o snapshot para a thread de disco e mantém o Event Loop ativo permitindo edições.

#### Scenario: Marcação de modificações ocorridas durante o salvamento
- **WHEN** o usuário faz novas alterações no editor enquanto a thread de salvamento ainda está executando em background
- **THEN** a UI marca essas novas alterações como "não salvas", isolando-as do snapshot atual em andamento.

#### Scenario: Salvamento concluído com sucesso
- **WHEN** a operação de gravação no disco/banco de dados do snapshot é finalizada com êxito na thread de background
- **THEN** a interface recebe o sinal de conclusão, atualiza seu marcador de estado salvo definindo a posição limpa do `QUndoStack` (histórico) exatamente no índice correspondente ao snapshot, remove o indicador de "Salvando..." e notifica sucesso.

#### Scenario: Erro no salvamento
- **WHEN** ocorre uma exceção durante as operações de I/O na thread de background
- **THEN** o erro é propagado para a thread principal e a interface exibe um `QMessageBox.critical` com os detalhes da falha, removendo imediatamente o estado de "Salvando...".

#### Scenario: Fechamento do app durante um salvamento ativo
- **WHEN** o usuário tenta fechar o aplicativo ou o aplicativo solicita saída enquanto a thread de salvamento ainda não concluiu
- **THEN** a UI deve interceptar a saída, exibir uma notificação modal de "Finalizando salvamento..." e aguardar a thread de I/O. Se a thread concluir com sucesso, o fechamento prossegue; se concluir com erro, o fechamento é cancelado, retornando ao estado de edição para que o usuário não perca dados.
