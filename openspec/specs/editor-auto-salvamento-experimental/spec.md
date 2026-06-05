## ADDED Requirements

### Requirement: Ciclo de Auto-Salvamento em Conexão Ativa
O sistema SHALL ativar um ciclo de salvamento e compilação automática sempre que houver uma conexão ativa com o celular.

#### Scenario: Ativação do auto-salvamento
- **WHEN** um celular é conectado ao editor
- **THEN** o sistema SHALL iniciar uma thread de monitoramento de inatividade

### Requirement: Detecção de Inatividade e Sincronização
O sistema SHALL detectar períodos de inatividade do usuário para disparar a sincronização dos dados.

#### Scenario: Disparo de salvamento automático
- **WHEN** a conexão com o celular está ativa
- **AND** o usuário passa 10 segundos sem interagir (sem cliques de mouse ou pressionar teclas)
- **AND** mesmo que o usuário mova o mouse sem clicar
- **THEN** o sistema SHALL:
    1. Salvar os dados atuais do croqui (`database/croqui.yaml`)
    2. Compilar o croqui para atualizar os artefatos em `compilado/`
    3. Notificar silenciosamente o servidor HTTPS de que há novos dados (para que o app móvel, fazendo polling, receba as mudanças)
