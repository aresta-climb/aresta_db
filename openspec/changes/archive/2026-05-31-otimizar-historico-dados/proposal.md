## Why

Atualmente, operações de Desfazer (Undo) e Refazer (Redo) na aba de Dados causam uma reconstrução completa de toda a árvore lateral e do formulário ativo, o que gera piscadas (flickers) na interface, perda do foco do campo que estava sendo editado e perda do estado de rolagem (scroll). Precisamos otimizar a atualização da interface para ser puramente incremental, alterando apenas os componentes estritamente afetados por um comando específico, oferecendo uma experiência nativa mais responsiva, fluida e amigável para edição contínua.

## What Changes

- Implementar uma arquitetura baseada em "Widgets Observadores" (Observer Pattern), onde cada widget de formulário gerado dinamicamente (para campos de texto, números, booleanos, etc.) passa a ouvir um barramento global de eventos do `GerenciadorHistorico`.
- Emitir um evento `sinal_campo_alterado` (contendo o ID da mensagem, o campo afetado e o novo valor) sempre que um comando sobre um campo primitivo for executado, desfeito ou refeito.
- Atualizar a UI focando o campo certo: o widget alvo recebe o sinal, atualiza seu conteúdo bloqueando re-emissão de comandos, e puxa para si o foco do teclado (`self.setFocus()`).
- Emitir sinais de mudança estrutural para coleções, como `item_adicionado(id_msg, campo, indice)` e `item_removido(id_msg, campo, indice)`, usados em operações de adição/remoção em `repeated` (listas) e troca de polimorfismo (`oneofs`).
- Modificar a geração de campos repetidos (`_render_repeated_field`) para que atue como um Container Observador, que insere (`layout.insertWidget`) e destrói instâncias específicas nos índices indicados pelas mudanças estruturais sem reconstruir seus layouts vizinhos.

## Capabilities

### New Capabilities
- `incremental-ui-updates`: Capacidade dos componentes da interface de refletirem alterações de estado granularmente por meio de eventos reativos para atualizações primitivas e estruturais sem provocar reconstrução completa do DOM/Qt Tree.

### Modified Capabilities
- `undo-redo-dados`: A capacidade existente de desfazer/refazer passa a delegar a reatividade das mudanças visuais a nível de widget em vez de solicitar um recarregamento macro da aba ou formulário em foco.

## Impact

- Impacta a forma como o `GerenciadorHistorico` notifica as views.
- Impacta o `WidgetFormularioPadrao` e `protobuf_widget_factory.py`, que precisarão conectar sinais/slots no momento de criação dos widgets e reagir a inserções/remoções estruturais.
- Otimização perceptível de performance em modelos de dados (croquis) pesados.
