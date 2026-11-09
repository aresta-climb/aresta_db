# editor-controle-mcp Spec Delta

## ADDED Requirements

### Requirement: Migração Atômica de Escalada entre Setores via MCP
O servidor MCP MUST disponibilizar a ferramenta `aresta_migrar_escalada` para mover uma `Escalada` de um `Setor` de origem para um `Setor` de destino em um único `CmdMacro`, resolvendo automaticamente o setor e o índice de origem a partir de `alvo_escalada` (UID ou caminho), preservando o `uid` da escalada, suas imagens em RAM e suas referências em mapas, e reindexando `IndiceUidsModel`.

#### Scenario: Migração de escalada entre setores informando apenas UID da escalada e UID do setor de destino
- **WHEN** o cliente MCP chama `aresta_migrar_escalada` informando `alvo_escalada` (UID da escalada) e `alvo_setor_destino` (UID ou caminho do setor de destino, com `indice_destino` opcional)
- **THEN** o servidor localiza automaticamente o setor de origem e o índice atual da escalada, executa `CroquiController.migrar_escalada` empilhando um único `CmdMacro` (`CmdRemoverRepeated` + `CmdAdicionarRepeated`), atualiza `IndiceUidsModel` e retorna `uid`, `setor_origem`, `indice_origem`, `setor_destino` e `indice_destino`

#### Scenario: Rejeição defensiva ao migrar alvo que não é uma Escalada ou setor inválido
- **WHEN** o cliente MCP chama `aresta_migrar_escalada` passando um `alvo_escalada` inexistente ou que não pertença à coleção `escaladas` de um `Setor`, ou um `alvo_setor_destino` inválido
- **THEN** o servidor MCP lança erro antes de empilhar qualquer comando na `QUndoStack` e retorna `isError: True` com mensagem descritiva

### Requirement: Alteração Multi-Alvo em Lote via MCP
O servidor MCP MUST disponibilizar a ferramenta `aresta_alterar_em_lote` que recebe uma lista não vazia `operacoes` (onde cada item define `alvo` e `campo`/`valor` ou `campos`), valida e coage todos os alvos e valores previamente (*fail-fast*) e despacha todas as mutações em um único `CmdMacro` atômico na pilha de histórico.

#### Scenario: Atualização atômica de múltiplas entidades distintas em uma única chamada MCP
- **WHEN** o cliente MCP chama `aresta_alterar_em_lote` passando `operacoes` com alterações em múltiplos `UID`s ou caminhos (incluindo campos primitivos, enums por nome, variantes `oneof`, submensagens e listas `repeated`)
- **THEN** o servidor coage todos os valores para seus tipos Protobuf, empilha um único `CmdMacro` via `CroquiController.alterar_em_lote`, reindexa `IndiceUidsModel` ao final e retorna a quantidade total de operações e alvos alterados, permitindo reverter todo o lote com um único `undo()`

#### Scenario: Atomicidade fail-fast quando uma operação do lote é inválida
- **WHEN** o cliente MCP chama `aresta_alterar_em_lote` com uma lista `operacoes` na qual qualquer item possui `alvo` inexistente, campo desconhecido ou valor incompatível com o `FieldDescriptor`
- **THEN** a chamada falha antes de executar ou empilhar qualquer subcomando na `QUndoStack`, mantendo o `CroquiModel` integralmente inalterado
