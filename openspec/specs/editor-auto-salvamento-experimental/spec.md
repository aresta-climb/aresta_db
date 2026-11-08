# editor-auto-salvamento-experimental Specification

## Purpose

Define o monitoramento de inatividade do usuário e o ciclo de salvamento e compilação automática enquanto a prévia ao vivo no celular estiver ativa no Editor Desktop.

## Requirements

### Requirement: Ciclo de Auto-Salvamento em Conexão Ativa
O sistema SHALL ativar um ciclo de salvamento e compilação automática sempre que houver uma conexão ativa com o celular.

#### Scenario: Ativação do auto-salvamento
- **WHEN** um celular é conectado ao editor
- **THEN** o sistema SHALL iniciar uma thread de monitoramento de inatividade

### Requirement: Detecção de Inatividade e Sincronização
O sistema SHALL detectar períodos de inatividade do usuário para disparar a sincronização automática dos dados apenas quando existirem modificações pendentes não salvas ou artefatos de prévia ausentes.

#### Scenario: Disparo de salvamento automático
- **WHEN** a conexão com o celular está ativa
- **AND** o usuário passa 10 segundos sem interagir (sem cliques de mouse ou pressionar teclas, mesmo que mova o mouse)
- **AND** existem alterações não salvas na pilha de histórico (`not isClean()`)
- **THEN** o sistema SHALL:
    1. Salvar os dados atuais do croqui (`database/croqui.yaml` e partes Markdown)
    2. Compilar incrementalmente o croqui para atualizar os artefatos em `compilado/`
    3. Emitir notificação de recarregamento para que o aplicativo móvel receba as mudanças

#### Scenario: Supressão de salvamento automático quando não há modificações
- **WHEN** a conexão com o celular está ativa e o temporizador de 10 segundos de inatividade expira
- **AND** a pilha de histórico está limpa (`isClean() == True`) e os artefatos compilados (`indice.binarypb` e `catalogo.db`) já existem em `compilado/`
- **THEN** o sistema NÃO DEVE disparar uma recompilação redundante em segundo plano, mantendo os arquivos de `compilado/` intactos e imediatamente disponíveis para download pelo aplicativo móvel
