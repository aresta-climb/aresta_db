# Spec Delta

## Purpose

Sincroniza bidirecionalmente a pasta de trabalho do croqui experimental com a branch remota da Pull Request no GitHub, oferecendo resolução atômica de conflitos no histórico do Git.

## ADDED Requirements

### Requirement: Sincronização Automática com Branch Remota da Pull Request
O sistema MUST verificar e baixar atualizações da branch remota vinculada ao croqui experimental ao carregar o croqui e antes de despachar novas publicações, aplicando merge automático quando não houver conflitos.

#### Scenario: Sincronização ao carregar croqui sem conflitos locais
- **WHEN** um croqui experimental associado a uma Pull Request aberta for carregado no editor e a branch remota possuir commits mais recentes
- **THEN** o sistema executa o fetch da branch remota e realiza o merge automático das alterações para a pasta local do croqui, recarregando a interface e emitindo notificação de sucesso

#### Scenario: Sincronização antes de publicação
- **WHEN** o usuário acionar o envio de uma atualização para uma Pull Request existente e houver novos commits na branch remota
- **THEN** o sistema realiza o fetch e merge das alterações remotas antes de gerar o commit e disparar o push das alterações locais

### Requirement: Ação Explícita de Sincronização na Barra de Ferramentas
A interface principal MUST disponibilizar uma ação de sincronização na barra de ferramentas superior, posicionada ao lado do botão de propor mudanças, com habilitação contextual baseada no estado do workspace e da Pull Request.

#### Scenario: Botão desabilitado sem Pull Request ativa
- **WHEN** o croqui em edição estiver em modo local ou não possuir Pull Request remota registrada em seus metadados experimentais
- **THEN** a ação de sincronização permanece desabilitada com tooltip explicativo

#### Scenario: Botão habilitado com Pull Request ativa
- **WHEN** o croqui possuir metadados de Pull Request ativa no GitHub e o workspace suportar publicação
- **THEN** a ação de sincronização é habilitada e, ao ser clicada, dispara a rotina de verificação e reconciliação remota

### Requirement: Resolução de Conflitos Preservada no Histórico do Git
Quando o merge automático entre a versão local e a remota falhar por conflito de edição, o sistema MUST abortar a mesclagem em disco sem corromper arquivos e solicitar a decisão do usuário, registrando o resultado em um commit de merge com duplo parentesco.

#### Scenario: Cancelamento da resolução de conflito
- **WHEN** ocorrer conflito na sincronização e o usuário optar por cancelar o diálogo
- **THEN** nenhuma alteração do GitHub é aplicada, a pasta de trabalho local permanece intacta e o repositório Git mantém seu estado original

#### Scenario: Resolução mantendo versão local
- **WHEN** ocorrer conflito e o usuário selecionar a opção de manter a versão local
- **THEN** o sistema cria um commit de merge combinando o commit local e o remoto com resolução a favor do conteúdo local, preservando o histórico de ambas as ramificações no Git

#### Scenario: Resolução adotando versão remota
- **WHEN** ocorrer conflito e o usuário selecionar a opção de adotar a versão do GitHub
- **THEN** o sistema cria um commit de merge combinando o commit local e o remoto com resolução a favor do conteúdo remoto, atualiza a pasta de trabalho com os arquivos do GitHub e recarrega os componentes da interface
