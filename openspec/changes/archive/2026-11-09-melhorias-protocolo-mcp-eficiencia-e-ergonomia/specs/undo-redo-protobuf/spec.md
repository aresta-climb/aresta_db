# undo-redo-protobuf Spec Delta

## ADDED Requirements

### Requirement: Sugestão de Campos Válidos em Erros de Campo Inexistente e Preservação Opt-In em Oneof
Quando um comando Protobuf ou validação de alvo receber um nome de campo inexistente na mensagem alvo, a exceção `ValueError` SHALL listar em ordem alfabética os nomes de campos e `oneofs` válidos do `DESCRIPTOR` daquela mensagem. Adicionalmente, `CroquiController.alterar_campo` e `alterar_em_lote` SHALL suportar `preservar_campos_compativeis: bool = False` na troca de ramo `oneof`, e `MapasController.remover_referencia` SHALL remover referências via comandos na `QUndoStack`.

#### Scenario: Mensagem de ValueError lista campos válidos quando campo não existe no DESCRIPTOR
- **WHEN** `CmdAlterarCampo` ou `validar_pertence_ao_croqui` é invocado com um `campo_nome` inexistente na mensagem alvo (ex.: `campo_nome="descricao"` em `ColecaoDeMapas`)
- **THEN** o `ValueError` lançado informa o nome da mensagem (`ColecaoDeMapas`) e inclui a lista ordenada dos campos válidos definidos no seu `DESCRIPTOR` (ex.: `mapas`)

#### Scenario: Remoção de referência em MapasController reversível via QUndoStack
- **WHEN** `MapasController.remover_referencia` é chamado para remover um subconjunto de `pontos_uids` ou uma `Referencia` completa de um `Mapa`
- **THEN** a mutação é executada via `CmdAlterarCampo` ou `CmdRemoverRepeated` (agrupados em `CmdMacro` se múltiplas entradas forem afetadas) e um único `undo()` restaura integralmente as referências anteriores
