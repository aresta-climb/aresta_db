# Proposta: Corrigir Mensagem Órfã ao Mover Itens Repeated no Editor

## Why

Ao reordenar itens de campos repetidos na árvore de dados do editor (por exemplo, "Mover para Cima" ou "Mover para Baixo" em um setor), tentativas subsequentes de modificar seus campos — ou a expiração do temporizador de coalescência de digitação pendente — falhavam com `ValueError: Mensagem alvo órfã detectada para o comando CmdAlterarPrimitivo: a mensagem do tipo 'Setor' não pertence à árvore ativa do croqui.`.

Isso ocorre porque contêineres de mensagens repetidas no Google Protobuf criam novas instâncias em memória quando `pop()` e `insert()` são invocados. A árvore de dados (`ProtobufTreeViewAdapter`) e o formulário (`FormularioPadrao`) mantinham as referências antigas (desanexadas/órfãs). É necessário sincronizar as referências de mensagens na árvore, descarregar preventivamente temporizadores de edição pendentes e atualizar/invalidar o cache do formulário para manter a integridade total do estado.

## What Changes

- **Sincronização recursiva de instâncias pós-movimento na árvore**: Atualizar `node.message` e nós filhos populados em `ProtobufTreeViewAdapter._on_item_movido` com as novas instâncias de mensagens geradas pelo Protobuf.
- **Flush preventivo de edições pendentes**: Forçar a consolidação de qualquer edição agendada no `TemporizadorCoalescencia` do formulário ou editor de Markdown antes de executar comandos de reordenação na árvore.
- **Invalidação e atualização de formulários em cache**: Garantir que `FormularioPadrao` invalide o cache associado à instância antiga do item movido e carregue os widgets vinculados à instância viva do Protobuf ao re-selecionar o nó.
- **Cobertura de testes automatizados**: Testes unitários e de integração cobrindo reordenação (cima/baixo), Undo/Redo, edição subsequente de primitivos/markdown e nós filhos populados (ex: trilhas/vias dentro de setores movidos).

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability necessária -->

### Modified Capabilities
- `editor-dados-arvore`: Exige que a árvore mantenha suas referências de mensagens válidas e vinculadas à árvore ativa do croqui após reordenações, sincronizando recursivamente a hierarquia de nós e permitindo edições posteriores sem detecção de orfandade.
- `editor-dados-formularios`: Exige que edições pendentes no formulário/editor sejam consolidadas antes da reordenação e que o formulário ativo reflita a nova instância viva da mensagem movida.

## Impact

- `editor/views/tree_view_adapter.py`: `_on_item_movido` e atualização recursiva de referências de mensagens.
- `editor/views/widget_editor_dados.py`: métodos `_executar_mover_para_cima`, `_executar_mover_para_baixo`, `_on_repeated_movido`, e ciclo de vida do `FormularioPadrao`.
- `editor/views/tree_view_adapter_test.py` e `editor/views/widget_editor_dados_test.py`: novos testes de regressão e garantia de 100% de cobertura.
