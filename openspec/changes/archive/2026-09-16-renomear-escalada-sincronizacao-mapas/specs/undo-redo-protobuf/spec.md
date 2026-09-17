## ADDED Requirements

### Requirement: Comandos Compostos Serializáveis (CmdMacro)
O sistema SHALL fornecer a classe `CmdMacro` para agrupar sequências ordenadas de comandos filhos derivados de `ComandoEditor`. O `CmdMacro` SHALL executar os comandos filhos em ordem no `executar_redo()`, em ordem reversa no `undo()`, e propagar `armar_carregamento_silencioso()` para todos os filhos. O `CmdMacro` SHALL implementar métodos `serializar()` e `deserializar()` completos para integração transparente com o `GerenciadorDiario` (`diario_pendente.bin` e `diario_salvo.bin`).

#### Scenario: Execução e reversão de macro
- **WHEN** um `CmdMacro` contendo múltiplos comandos filhos for executado na `QUndoStack`
- **THEN** todos os subcomandos SHALL ser aplicados em ordem no modelo
- **WHEN** o usuário aciona Desfazer (Undo)
- **THEN** todos os subcomandos SHALL ser revertidos em ordem inversa de forma atômica em um único passo da pilha

#### Scenario: Serialização e restauração do diário
- **WHEN** um `CmdMacro` for gravado no `diario_pendente.bin` e posteriormente restaurado via `deserializar_comando`
- **THEN** todos os subcomandos SHALL ser perfeitamente reconstruídos com suas classes e parâmetros originais sem perda de dados

### Requirement: Proibição Arquitetural de Macros Nativos do Qt
O sistema SHALL proibir qualquer chamada direta aos métodos `beginMacro` ou `endMacro` do `QUndoStack` do PySide6 em todo o código-fonte do editor, prevenindo o descarte silencioso de operações pelo diário de persistência. Essa restrição SHALL ser validada de forma automatizada pela suíte de testes de arquitetura.

#### Scenario: Detecção de uso indevido de beginMacro/endMacro
- **WHEN** a suíte de testes de arquitetura (`arquitetura_mvc_test.py`) analisar o código do editor via AST
- **THEN** nenhuma invocação a `beginMacro` ou `endMacro` SHALL ser encontrada
- **WHEN** algum arquivo introduzir chamada a `beginMacro` ou `endMacro`
- **THEN** o teste de arquitetura SHALL falhar imediatamente com mensagem explicativa instruindo o uso de `CmdMacro`

### Requirement: Comando Atômico de Renomeação de Escalada (CmdRenomearEscalada)
O sistema SHALL fornecer `CmdRenomearEscalada` para encapsular a renomeação de uma escalada e a atualização concomitante de todas as referências em mapas (`mapa.referencias`) que apontam para essa escalada no mesmo pico. O comando SHALL suportar mesclagem contínua (`mergeWith`) delimitada pela sessão de foco do usuário.

#### Scenario: Renomeação atômica de escalada e referências
- **WHEN** `CmdRenomearEscalada` for executado para alterar o nome de uma escalada de `Nome A` para `Nome B`
- **THEN** o nome da escalada no modelo SHALL ser alterado para `Nome B`
- **THEN** todas as mensagens `croqui_pb2.Mapa.Referencia` previamente identificadas como vinculadas àquela escalada SHALL ter seu campo `escalada` atualizado para `Nome B`
- **WHEN** o comando for desfeito (Undo)
- **THEN** tanto a escalada quanto todas as referências vinculadas SHALL retornar ao `Nome A` em um único passo
