## ADDED Requirements

### Requirement: Guarda de Integridade Estrutural nos Comandos Protobuf
O sistema SHALL validar a pertinência da mensagem alvo à árvore ativa do croqui na instanciação de qualquer comando Protobuf que opere sobre mensagens filhas (`CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdAlterarRepeatedItem`, `CmdAlterarMultiplosRepeatedItems`, `CmdMoverRepeated`, `CmdAlterarOneof`, `CmdAlterarPrimitivo`, `CmdAlterarCampoImagem`). Se a mensagem alvo não for o nó raiz `Croqui` e o caminho resolvido na árvore ativa for vazio `""`, o comando SHALL lançar imediatamente `ValueError`, impedindo comandos órfãos de entrarem no histórico (`QUndoStack`) ou no diário de persistência. O sistema também SHALL validar que o campo informado pertença aos campos do descriptor da mensagem alvo.

#### Scenario: Tentativa de criação de comando com mensagem desanexada/órfã
- **WHEN** um comando de alteração estrutural ou de campo for instanciado com uma mensagem que não pertence à árvore do `CroquiModel`
- **THEN** o comando SHALL disparar `ValueError` descrevendo que a mensagem alvo é órfã, impedindo a sua execução e gravação no diário

#### Scenario: Criação de comando legítimo na mensagem raiz ou mensagem filha conectada
- **WHEN** um comando for instanciado para alterar um campo da mensagem raiz `Croqui` ou de uma mensagem filha conectada à árvore
- **THEN** o comando SHALL ser criado com sucesso, resolvendo o caminho correto e permitindo execução e serialização normais

#### Scenario: Deserialização de comando com caminho corrompido ou campo inexistente
- **WHEN** o histórico ou diário tentar deserializar um comando cujo caminho seja inválido ou o campo não exista na mensagem resultante
- **THEN** o sistema SHALL registrar o erro em log e descartar o comando com segurança, permitindo que a recuperação de sessão continue sem travar o editor
