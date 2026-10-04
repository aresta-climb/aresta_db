# Spec Delta

## MODIFIED Requirements

### Requirement: Tratamento de Falhas na Inicialização
A aplicação MUST informar ao usuário se ocorrer um erro crítico que impeça a abertura do editor e MUST continuar a inicialização em modo offline caso a falha de sincronização remota ocorra sobre uma base local já existente.

#### Scenario: Erro de Rede ou Disco
- **WHEN** ocorrer uma falha irrecuperável durante a inicialização
- **THEN** a aplicação MUST ocultar a `TelaDeAbertura` e exibir uma caixa de mensagem de erro crítica
- **THEN** se o erro for 404 em repositório da organização, a mensagem MUST instruir sobre permissões no GitHub

#### Scenario: Falha Não Crítica de Sincronização com Base Existente
- **WHEN** ocorrer uma falha de conexão de rede durante a sincronização de dados remotos e a base local de croquis já existir no disco
- **THEN** a aplicação MUST registrar um aviso no log e emitir atualização de status na interface
- **THEN** a aplicação MUST prosseguir normalmente com a inicialização e abrir o editor utilizando os dados locais
