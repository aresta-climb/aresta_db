# Spec Delta: undo-redo-protobuf

## MODIFIED Requirements

### Requirement: Resolução Tardia de Mensagens Alvo em Comandos Protobuf
Os comandos derivados de `ComandoEditor` que operam sobre mensagens da árvore Protobuf SHALL utilizar resolução tardia (*lazy resolution*) através de `caminho_msg`. A mensagem alvo viva no modelo SHALL ser resolvida dinamicamente no momento da execução das operações de `undo()` e `executar_redo()`. Caso a mensagem alvo não exista, esteja fora dos limites de repetição ou inacessível, o sistema SHALL tratar a falha através da exceção tipada `MensagemAlvoNaoEncontradaError(LookupError)` ou retorno `None` seguro, abortando a operação sem corromper a árvore e sem emitir sinais reativos com identificador nulo.

#### Scenario: Execução de undo com mensagem alvo existente via caminho
- **WHEN** o usuário aciona Desfazer (Undo) em um comando deserializado ou executado previamente
- **THEN** o comando navega pelo `caminho_msg` na árvore atual do modelo, localiza a instância viva correspondente e aplica a reversão com sucesso

#### Scenario: Execução de undo com mensagem alvo inexistente ou índice fora de limite
- **WHEN** o usuário aciona Desfazer (Undo) e a mensagem alvo não pode ser resolvida pelo `caminho_msg` (por exemplo, nó excluído ou índice inexistente)
- **THEN** o comando SHALL registrar uma mensagem de erro explícita em log reportando a falha de reversão do alvo e não aplicar mutações inconsistentes no modelo

#### Scenario: Navegação segura com tratamento de limites e oneofs inativos
- **WHEN** o sistema navega pela árvore do modelo através de um caminho contendo índices de lista ou seleções de `oneof`
- **THEN** o navegador SHALL verificar os limites de repetição da lista antes de indexar e verificar se a variante do `oneof` está ativa, retornando `None` de forma segura caso o caminho seja inválido em vez de disparar exceções não tratadas

#### Scenario: Despacho de sinal ignora comando com mensagem alvo nula ou não resolvida
- **WHEN** o despachante de sinais do histórico processa um comando cuja mensagem alvo não pôde ser resolvida no modelo
- **THEN** o despachante SHALL descartar a emissão de sinais reativos de campo ou item, prevenindo a propagação de eventos inconsistentes com `id(None)`
