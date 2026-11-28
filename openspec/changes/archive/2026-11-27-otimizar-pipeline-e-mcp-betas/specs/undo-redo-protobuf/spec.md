# Delta Specification: undo-redo-protobuf

## MODIFIED Requirements

### Requirement: Migração de Escalada e Alteração Multi-Alvo em Lote via CmdMacro
O `CroquiController` SHALL disponibilizar os métodos compostos `migrar_escalada` (combinando `CmdRemoverRepeated` no setor de origem e `CmdAdicionarRepeated` no setor de destino sem expurgar imagens da escalada em RAM) e `alterar_em_lote` (instanciando e validando previamente todos os comandos de múltiplos alvos antes de empilhar um único `CmdMacro` na `QUndoStack`). Ao construir subcomandos múltiplos para um mesmo alvo em `_construir_comandos_para_alvo`, `adicionar_multiplos_repeated` e `alterar_multiplos_repeated_items`, o controller SHALL resolver e validar o caminho canônico `caminho_res` uma única vez e repassar a string `alvo=caminho_res` aos comandos folha sem repetir varreduras DFS $O(\text{Croqui})$ na árvore. O `CroquiModel` SHALL reconstruir `IndiceUidsModel` em operações `repeated` (`_adicionar_repeated`, `_remover_repeated`, `_mover_repeated`, `_alterar_repeated_item`) exclusivamente quando `campo_nome` pertencer ao conjunto de coleções com UIDs indexados (`botoes`, `picos`, `setores_ou_grupos`, `setores`, `escaladas`, `enfiadas`), evitando reconstruções repetitivas em coleções de curadoria ou anexos auxiliares.

#### Scenario: Migração de escalada preserva imagens em RAM e reverte em um único Undo
- **WHEN** `CroquiController.migrar_escalada` move uma `Escalada` contendo imagens associadas de um `Setor` de origem para um `Setor` de destino
- **THEN** as imagens em memória RAM da escalada são preservadas durante o `redo()`, o `uid` da escalada permanece inalterado no setor de destino, e um único `undo()` restaura a escalada ao setor e índice originais

#### Scenario: Alteração em lote multi-alvo valida todos os comandos antes de empilhar CmdMacro
- **WHEN** `CroquiController.alterar_em_lote` recebe uma sequência de operações para diferentes alvos da árvore Protobuf
- **THEN** todos os comandos folha (`CmdAlterarCampo`, `CmdRemoverRepeated`, `CmdAdicionarRepeated`) são instanciados e validados antes de empilhar um único `CmdMacro` na `QUndoStack`, garantindo reversão integral em um passo de `undo()`

#### Scenario: Alteração em lote sobre coleções de curadoria executa em tempo sub-segundo sem reindexar UIDs
- **WHEN** `CroquiController.alterar_em_lote` substitui dezenas de listas `betas_nao_scorados` e `betas_nao_revisados` em um croqui populado com milhares de `betas_rejeitados`
- **THEN** o controller reutiliza o caminho canônico em $O(1)$ nos subcomandos gerados, o `CroquiModel` não dispara reconstrução do `IndiceUidsModel` nem emite `indice_alterado`, e o lote completo conclui em menos de `200 ms` com reversão atômica por um único `undo()`
