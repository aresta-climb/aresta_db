## ADDED Requirements

### Requirement: Salvamento de croqui não bloqueante
O sistema SHALL executar as rotinas de persistência do croqui (disco/banco de dados) em uma thread separada (background), evitando qualquer congelamento da interface principal.

#### Scenario: Iniciando salvamento
- **WHEN** o usuário aciona a ação de "Salvar" (via botão ou atalho de teclado)
- **THEN** a interface de usuário exibe um indicador visual (estado de "Salvando..."), desabilita ações conflitantes para evitar inconsistências de dados e mantém sua responsividade (Event Loop ativo).

#### Scenario: Salvamento concluído com sucesso
- **WHEN** a operação de gravação no disco/banco de dados é finalizada com êxito na thread de background
- **THEN** a interface recebe o sinal de conclusão, remove o estado de "Salvando...", reabilita a UI e registra o sucesso da operação.

#### Scenario: Erro no salvamento
- **WHEN** ocorre uma exceção durante as operações de I/O na thread de background
- **THEN** o erro é propagado para a thread principal e a interface exibe um `QMessageBox.critical` com os detalhes da falha, removendo imediatamente o estado de "Salvando...".
