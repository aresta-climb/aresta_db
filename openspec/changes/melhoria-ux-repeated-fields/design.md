## Context

No editor de dados (feito em PyQt), mensagens protobuf que contêm listas de objetos complexos (`repeated fields` de mensagens) são atualmente renderizadas em sua totalidade assim que o nó pai (como Setor) é selecionado. Como o formulário tenta instanciar milhares de widgets (QLineEdits, QComboBoxes, layouts) na mesma thread da UI, o aplicativo trava por aproximadamente 0.5s e a página fica excessivamente longa e poluída para o usuário.

## Goals / Non-Goals

**Goals:**
- Melhorar a performance e a legibilidade da interface de edição de dados aninhados.
- Criar blocos colapsáveis (Acordeões) para itens repetidos.
- Implementar instanciação sob demanda (Lazy Loading) do conteúdo dos acordeões.
- Usar uma heurística inteligente para apresentar nomes descritivos no título dos itens da lista.
- Garantir 100% de cobertura nos fluxos de TDD e integração contínua (Undo/Redo).

**Non-Goals:**
- Não reescreveremos o gerador dinâmico do formulário inteiro (não iremos forçar uma refatoração total de MVC para o `widget_editor_dados.py`).
- Não migraremos para Model/View nativo (como QListView/QItemDelegate) para a exibição dos formulários dinâmicos aninhados.

## Decisions

- **Uso de Blocos Colapsáveis (Acordeão)**: O `_render_repeated_field` instanciará um botão de título ao invés do layout estendido do item. Isso mantém a UI compatível com o conceito de um formulário único e scrolável, mas esconde a complexidade.
- **Lazy Load de Widgets**: O método de renderização não chamará de imediato o `_render_message_fields` para submensagens da lista. Essa rotina será envelopada numa função de callback (thunk/task) associada ao evento de `toggled` (expandir) do bloco colapsável.
- **Heurística de Cabeçalho**: Foi decidido que iterar os campos buscando por `nome`, `titulo` ou `id` é suficiente para 90% dos casos do domínio da aplicação. Essa lógica fará a busca em tempo de "collapse" para não ser pesada.
- **Interação com Undo/Redo**: Em caso de reversão (Undo) pelo histórico do PyQt:
  1. Se o campo modificado não estiver instanciado (acordeão ainda fechado), o `_on_campo_alterado` apenas não atualizará o UI (o protobuf subjacente já foi modificado pelo controller).
  2. A interface deverá atualizar o título do acordeão dinamicamente caso o campo afetado pelo Undo/Redo seja um dos campos chave (id, nome, etc).

## Risks / Trade-offs

- **Risco**: Validação de dados. Como campos não renderizados não possuem widgets na tela, não recebem foco ou avisos de validação do Qt diretamente.
  - *Mitigação*: A validação de negócio na lógica da camada de modelo do Protobuf já pega o erro de qualquer forma na tentativa de salvar.
- **Risco**: Atualização de eventos (`_on_campo_alterado`). Se o campo foi alterado por um "undo" mas o formulário ainda não foi expandido (lazy load), não devemos causar crashes ao tentar atualizar um QLineEdit inexistente.
  - *Mitigação*: Devemos tratar com cuidado a ausência do widget caso ele ainda não tenha sido instanciado, e propagar um sinal de "atualizar título" se aplicável.
