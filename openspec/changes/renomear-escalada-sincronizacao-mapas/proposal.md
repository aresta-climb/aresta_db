# Proposta: Sincronização Automática de Referências em Mapas ao Renomear Escaladas e CmdMacro Serializável

## Why

No modelo de dados do Aresta (`croqui.proto`), as referências em mapas (`croqui_pb2.Mapa.Referencia`) associam nós e traçados visuais a entidades lógicas utilizando o nome da escalada (`ref.escalada`). Quando um usuário altera o nome de uma escalada no formulário de dados do editor, as referências de mapa existentes tornam-se órfãs, quebrando os vínculos gráficos e causando falhas na compilação (`validar_referencias_mapa`). Além disso, macros criadas diretamente com `QUndoStack.beginMacro`/`endMacro` do Qt geram comandos C++ que não possuem método `serializar()`, sendo silenciosamente descartadas pelo diário de persistência (`diario_pendente.bin`).

Esta mudança resolve ambos os problemas: introduz um comando atômico `CmdRenomearEscalada` que atualiza a escalada e todas as referências correlatas nos mapas em uma única transação de Undo/Redo com suporte a mesclagem contínua (`mergeWith`) delimitada por sessão de foco, e introduz `CmdMacro` para envelopar operações compostas de forma 100% serializável no diário, com validação arquitetural via AST para proibir o uso de `beginMacro`/`endMacro` do Qt.

## What Changes

- **Renomeação Transparente de Escaladas**: Ao editar o campo `nome` de uma escalada no formulário de dados (`WidgetEditorDados`), o controlador dispara `CmdRenomearEscalada`, buscando e atualizando atomicamente todas as referências em mapas no mesmo pico que apontam para a via/boulder.
- **Resolução Simétrica de Escopo**: Criação da biblioteca `referencias_util.py` para identificar com precisão o vínculo das referências considerando tanto o setor quanto o grupo efetivo (implícito ou explícito).
- **Delimitação de Sessão de Foco (`session_id`)**: A mesclagem contínua de digitação (`mergeWith`) passa a ser restrita ao ciclo de vida de foco do campo (`focusInEvent` a `focusOutEvent`), garantindo que novas interações com o campo refaçam a busca a partir do estado atual da árvore sem reutilizar referências defasadas.
- **Comando Composto `CmdMacro`**: Implementação de `CmdMacro(ComandoEditor)` com suporte total a `executar_redo()`, `undo()` reverso, `serializar()`, `deserializar()` e propagação de `armar_carregamento_silencioso()`.
- **Migração de Macros do Qt**: Substituição de `pilha.beginMacro()` e `pilha.endMacro()` em `mapas_controller.py` e `widget_editor_mapas.py` por `CmdMacro`.
- **Teste de Arquitetura**: Nova regra em `editor/arquitetura_mvc_test.py` analisando a AST do código para barrar estritamente qualquer chamada direta a `beginMacro` ou `endMacro` do Qt em favor do `CmdMacro`.

## Capabilities

### Modified Capabilities
- `undo-redo-protobuf`: Incorpora `CmdMacro` serializável no diário, `CmdRenomearEscalada` com suporte a `mergeWith` delimitado por sessão de foco, e regra arquitetural impedindo `beginMacro`/`endMacro`.
- `editor-mapas-referencias`: Garante atualização reativa e integridade referencial atômica de `ref.escalada` em todos os mapas pertinentes quando a escalada é renomeada no editor.

## Impact

- **Modelos e Comandos (`editor/commands/`)**: Novo comando `CmdRenomearEscalada` e `CmdMacro` registrados na factory de deserialização (`deserializar_comando`).
- **Controladores (`editor/controllers/`)**: `CroquiController.alterar_primitivo` roteia edições no campo `nome` de escaladas para `CmdRenomearEscalada`. `MapasController` migra do macro nativo do Qt para `CmdMacro`.
- **Visões (`editor/views/`)**: `WidgetEditorDados` integra `session_id` no ciclo de foco do campo de edição de nome.
- **Testes**: Novos testes unitários para `referencias_util`, `CmdRenomearEscalada`, `CmdMacro` e ampliação de `arquitetura_mvc_test.py`.
