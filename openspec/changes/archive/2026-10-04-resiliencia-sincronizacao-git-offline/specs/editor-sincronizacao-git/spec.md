# Spec Delta

## ADDED Requirements

### Requirement: Resiliência e Degradação Graciosa na Sincronização Remota
A aplicação MUST tratar falhas de rede, timeouts de conexão e erros de transporte durante a sincronização remota sem interromper a execução quando o repositório local já existir no disco.

#### Scenario: Falha de Conexão com Base Local Existente
- **WHEN** o comando de `fetch` remoto falhar por timeout, desconexão ou falha de canal seguro e o repositório local já estiver presente
- **THEN** a aplicação MUST suprimir o encerramento do processo
- **THEN** a aplicação MUST emitir um aviso informativo de operação em modo offline e continuar a inicialização

#### Scenario: Tratamento de Credenciais em Repositório Público
- **WHEN** o usuário realizar clone ou fetch no repositório base público
- **THEN** a aplicação MUST abster-se de injetar tokens de autorização de usuário propensos a expiração
- **THEN** caso a biblioteca subjacente consulte o callback de credenciais sem token disponível, o sistema MUST sinalizar `Passthrough` em vez de retornar valor nulo

#### Scenario: Diagnóstico Legível de Falhas do Git
- **WHEN** o motor Git nativo reportar um erro genérico com mensagem vazia ou "no error" decorrente de esgotamento de tentativas no Windows
- **THEN** a biblioteca de sincronização MUST traduzir a exceção para um `ErroSincronizacaoGit` com mensagem clara indicando tempo limite esgotado ou falha de conexão de rede
