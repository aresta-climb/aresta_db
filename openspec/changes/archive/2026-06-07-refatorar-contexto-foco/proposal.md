## Why

Atualmente, o sistema de foco na aplicação não funciona de maneira global. Quando o usuário clica em Desfazer (Undo) após fazer edições em abas diferentes (ex: na aba de Mapas e na aba de Dados), o sistema emite eventos de foco mas não troca automaticamente para a aba correta nem carrega o documento correspondente. Isso gera confusão, pois as mudanças visuais do *undo* não são exibidas na tela caso a aba ativa seja outra. O formato do caminho de foco (context path) era restrito ao `WidgetEditorDados`.

## What Changes

- Refatorar o sistema de foco para usar strings compostas e universais (como URIs) (ex: `page:dados/node:root/...` ou `page:mapas/file:setor_x.md`), unificando o contexto de UI de toda a aplicação.
- A `JanelaPrincipal` passa a escutar os eventos de foco para rotear (trocar) a aba ativa de acordo com o prefixo da string de contexto.
- Criar uma classe utilitária (ex: `ContextoUIPath`) para encapsular o parsing e tratamento da string de contexto, permitindo manipulações idiomáticas (ex: remover prefixos).
- Atualizar todos os comandos (`QUndoCommand`) para que armazenem a string global de contexto da UI no momento em que são criados, e então notifiquem o sistema para restaurar esse contexto durante o `undo()` e `redo()`.

## Capabilities

### New Capabilities
- `contexto-foco-global`: Implementação do sistema unificado de contexto de interface baseado em URIs, permitindo restauração do estado de navegação.

### Modified Capabilities

## Impact

- `legacy_views/area_principal.py` (JanelaPrincipal): Vai assinar e reagir ao `foco_requisitado`.
- `core/historico.py`: Opcionalmente criar sinalização global.
- `commands/comandos_protobuf.py` e `controllers/croqui_controller.py`: Receber e despachar a nova string.
- `legacy_views/editor_mapas.py`: Modificar os comandos nativos (como o `CmdMoverPonto`) para suportarem o `contexto_ui`.
