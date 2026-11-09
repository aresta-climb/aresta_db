# undo-redo-protobuf Spec Delta

## ADDED Requirements

### Requirement: Migração de Escalada e Alteração Multi-Alvo em Lote via CmdMacro
O `CroquiController` SHALL disponibilizar os métodos compostos `migrar_escalada` (combinando `CmdRemoverRepeated` no setor de origem e `CmdAdicionarRepeated` no setor de destino sem expurgar imagens da escalada em RAM) e `alterar_em_lote` (instanciando e validando previamente todos os comandos de múltiplos alvos antes de empilhar um único `CmdMacro` na `QUndoStack`).

#### Scenario: Migração de escalada preserva imagens em RAM e reverte em um único Undo
- **WHEN** `CroquiController.migrar_escalada` move uma `Escalada` contendo imagens associadas de um `Setor` de origem para um `Setor` de destino
- **THEN** as imagens em memória RAM da escalada são preservadas durante o `redo()`, o `uid` da escalada permanece inalterado no setor de destino, e um único `undo()` restaura a escalada ao setor e índice originais

#### Scenario: Alteração em lote multi-alvo valida todos os comandos antes de empilhar CmdMacro
- **WHEN** `CroquiController.alterar_em_lote` recebe uma sequência de operações para diferentes alvos da árvore Protobuf
- **THEN** todos os comandos folha (`CmdAlterarCampo`, `CmdRemoverRepeated`, `CmdAdicionarRepeated`) são instanciados e validados antes de empilhar um único `CmdMacro` na `QUndoStack`, garantindo reversão integral em um passo de `undo()`
