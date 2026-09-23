## MODIFIED Requirements

### Requirement: Guarda de Integridade Estrutural nos Comandos Protobuf
O sistema SHALL validar a pertinência da mensagem alvo à árvore ativa do croqui na instanciação direta de qualquer comando Protobuf originado por ações do usuário em tempo de execução (`CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdAlterarRepeatedItem`, `CmdAlterarMultiplosRepeatedItems`, `CmdMoverRepeated`, `CmdAlterarOneof`, `CmdAlterarPrimitivo`, `CmdAlterarCampoImagem`). Se a mensagem alvo não for o nó raiz `Croqui` e o caminho resolvido na árvore ativa for vazio `""`, o comando SHALL lançar imediatamente `ValueError`, impedindo comandos órfãos de entrarem no histórico (`QUndoStack`) ou no diário de persistência. Na deserialização a partir do diário persistido, o comando SHALL aceitar o `caminho_msg` armazenado sem validação prematura ou navegação imediata na árvore viva, postergando a resolução do alvo para o momento da execução (`undo`/`redo`).

#### Scenario: Tentativa de criação de comando com mensagem desanexada/órfã
- **WHEN** um comando de alteração estrutural ou de campo for instanciado diretamente via interface com uma mensagem que não pertence à árvore do `CroquiModel`
- **THEN** o comando SHALL disparar `ValueError` descrevendo que a mensagem alvo é órfã, impedindo a sua execução e gravação no diário

#### Scenario: Criação de comando legítimo na mensagem raiz ou mensagem filha conectada
- **WHEN** um comando for instanciado para alterar um campo da mensagem raiz `Croqui` ou de uma mensagem filha conectada à árvore
- **THEN** o comando SHALL ser criado com sucesso, resolvendo o caminho correto e permitindo execução e serialização normais

#### Scenario: Deserialização de comando com caminho corrompido ou campo inexistente
- **WHEN** o histórico ou diário tentar deserializar um comando cujo caminho seja inválido ou o campo não exista na mensagem resultante
- **THEN** o sistema SHALL registrar o erro em log e descartar o comando com segurança, permitindo que a recuperação de sessão continue sem travar o editor

#### Scenario: Deserialização declarativa a partir do diário
- **WHEN** o histórico ou diário deserializar um comando a partir dos dados gravados em disco
- **THEN** o comando SHALL ser reconstruído com seu `caminho_msg` sem navegar imediatamente na árvore do modelo e sem disparar validação prematura de pertencimento

## ADDED Requirements

### Requirement: Resolução Tardia de Mensagens Alvo em Comandos Protobuf
Os comandos derivados de `ComandoEditor` que operam sobre mensagens da árvore Protobuf SHALL utilizar resolução tardia (*lazy resolution*) através de `caminho_msg`. A mensagem alvo viva no modelo SHALL ser resolvida dinamicamente no momento da execução das operações de `undo()` e `executar_redo()`. Caso a mensagem alvo não exista, esteja fora dos limites de repetição ou inacessível no momento da execução, o comando SHALL registrar um erro explícito no log e abortar a operação sem corromper a árvore do modelo.

#### Scenario: Execução de undo com mensagem alvo existente via caminho
- **WHEN** o usuário aciona Desfazer (Undo) em um comando deserializado ou executado previamente
- **THEN** o comando navega pelo `caminho_msg` na árvore atual do modelo, localiza a instância viva correspondente e aplica a reversão com sucesso

#### Scenario: Execução de undo com mensagem alvo inexistente ou índice fora de limite
- **WHEN** o usuário aciona Desfazer (Undo) e a mensagem alvo não pode ser resolvida pelo `caminho_msg` (por exemplo, nó excluído ou índice inexistente)
- **THEN** o comando SHALL registrar uma mensagem de erro explícita em log reportando a falha de reversão do alvo e não aplicar mutações inconsistentes no modelo

#### Scenario: Navegação segura com tratamento de limites e oneofs inativos
- **WHEN** o sistema navega pela árvore do modelo através de um caminho contendo índices de lista ou seleções de `oneof`
- **THEN** o navegador SHALL verificar os limites de repetição da lista antes de indexar e verificar se a variante do `oneof` está ativa, retornando `None` de forma segura caso o caminho seja inválido em vez de disparar exceções não tratadas
