## Why

Recentemente foi identificado um cenário crítico em que operações no editor de mapas (adição de POIs, traçados vetoriais e referências) foram executadas sobre uma instância em memória desanexada/órfã da mensagem `Mapa`. Isso ocorreu porque o `WidgetEditorMapas` manteve a referência `self.msg_mapa_proxy` após o mapa correspondente ter sido removido/substituído estruturalmente na árvore do croqui (`CroquiModel`).

Como consequência, comandos como `CmdAdicionarRepeated` e `CmdAlterarRepeatedItem` resolveram o caminho da mensagem como `""` (vazio) via `resolver_caminho_mensagem()`, pois a mensagem não constava mais na árvore do croqui raiz. No entanto, o sistema aceitou a criação dos comandos silenciosamente e persistiu dezenas de operações zumbis com `caminho_msg: ""` no diário pendente e no diário salvo. Ao reabrir o editor ou tentar recuperar a sessão, esses comandos falharam na deserialização ou no replay (pois `""` aponta para a raiz `Croqui`, que não possui campos de mapa como `pontos_de_interesse`), causando perda de dados e travamento do diário.

Esta alteração é necessária para blindar a integridade estrutural do sistema em duas frentes complementares: impedir a instanciação e gravação de comandos órfãos na camada de `commands/`, e garantir sincronização reativa imediata e guarda de validação na camada de visualização `WidgetEditorMapas`.

## What Changes

- **Guarda de Integridade Estrutural nos Comandos (`comandos_protobuf.py`)**:
  - Implementar validação rigorosa na instanciação e execução de comandos que atuam sobre mensagens filhas do croqui (`CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdAlterarRepeatedItem`, `CmdAlterarMultiplosRepeatedItems`, `CmdMoverRepeated`, `CmdAlterarOneof`, `CmdAlterarPrimitivo`, `CmdAlterarCampoImagem`, etc.).
  - Se a mensagem alvo não for o nó raiz `Croqui` e o caminho resolvido (`resolver_caminho_mensagem`) retornar vazio `""` (ou `None`), disparar imediatamente uma exceção (`ValueError`), impedindo que comandos órfãos/fantasmas entrem no histórico (`QUndoStack`) ou no diário binário.
  - Validar também que o campo informado (`campo_nome`) existe no `DESCRIPTOR` da mensagem alvo correspondente.
- **Tolerância a Falhas na Deserialização de Comandos Antigos**:
  - Garantir que a deserialização ou replay de comandos com mensagens corrompidas ou campos inexistentes registre log de erro e ignore a entrada órfã, sem interromper abruptamente a abertura do projeto ou o replay de comandos íntegros.
- **Sincronização Reativa de Mapas no `WidgetEditorMapas`**:
  - Conectar o `WidgetEditorMapas` aos eventos reativos de remoção e adição de itens repeated do modelo quando `campo_nome == 'mapas'`.
  - Ao detectar a remoção ou substituição de mapas, reconstruir a lista lateral de mapas e, se o mapa atualmente visualizado (`self.msg_mapa_proxy`) tiver sido removido ou não pertencer mais à árvore ativa do croqui, descarregar a cena visual, desmarcar a seleção ou selecionar o primeiro mapa disponível.
  - Adicionar guarda preventiva nos métodos de interação do `WidgetEditorMapas` (adição de POIs, desenho de linhas, manipulação de nós e referências), impedindo mutações caso o mapa ativo não pertença à árvore do croqui.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability criada; as alterações estendem capacidades existentes. -->

### Modified Capabilities
- `undo-redo-protobuf`: Adiciona requisito de guarda de integridade estrutural e validação de pertinência da mensagem à árvore ativa nos comandos Protobuf.
- `editor-mapas`: Adiciona requisito de sincronização reativa estrutural de mapas e guarda de validação de mapa ativo no `WidgetEditorMapas`.

## Impact

- **Módulos Afetados**:
  - `editor/commands/comandos_protobuf.py`: Validação de nó órfão em construtores de comandos e função auxiliar de validação.
  - `editor/views/widget_editor_mapas.py`: Tratamento de sinais reativos para lista de mapas e verificação de mapa ativo antes de despachar comandos.
  - `editor/core/historico.py` e `editor/commands/comandos_protobuf.py`: Resiliência contra comandos inválidos em deserialização.
- **Compatibilidade e Dados**:
  - Previne 100% de comandos zumbis no `diario_pendente.bin` e `diario_salvo.bin`.
  - Não altera o schema Protobuf (`croqui.proto`), mantendo total compatibilidade retroativa com arquivos YAML e Markdown existentes.
