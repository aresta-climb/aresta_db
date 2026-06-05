## Why

Atualmente, o editor de dados exibe cada campo individual do protobuf na árvore do lado esquerdo e apenas um campo por vez no formulário do lado direito. Isso torna a edição e navegação de croquis ineficientes, poluindo a visualização da árvore e fragmentando os dados do formulário.

## What Changes

- A árvore de navegação do editor de dados (`editor-dados-arvore`) será simplificada para exibir apenas sub-mensagens do `Croqui` que estejam explicitamente anotadas com a opção de mensagem `MensagemFormatoUi.SEPARADO` ou `MensagemFormatoUi.ONEOF_CONTEUDO`.
- Campos repetidos (`repeated`) contendo mensagens elegíveis na árvore serão exibidos agrupados sob um nó agrupador intermediário ("expando"), listando seus itens individualmente após sua expansão.
- A área de formulário (`editor-dados-formularios`) passará a renderizar todos os campos da mensagem selecionada em um formulário único e coeso.
- Cada campo no formulário exibirá seu nome (obtido do field option `ui_label` ou gerado amigavelmente a partir do nome do campo), sua descrição (comentário presente no protobuf) e botões para gerenciar a presença do valor (adicionar, modificar ou remover valor).
- Sub-mensagens anotadas com `MensagemFormatoUi.INLINE` serão incorporadas diretamente no formulário da mensagem pai, formatadas em uma sub-área inline delimitada por bordas, não margens.
- A árvore atualizará dinamicamente seu conteúdo com base nas adições/remoções de sub-mensagens estruturais.

## Capabilities

### New Capabilities

*(Nenhuma nova capacidade no nível de especificação global, apenas refatoração das existentes)*

### Modified Capabilities

- `editor-dados-arvore`: A navegação da árvore será reestruturada para operar no nível de abstração de mensagem, exibindo apenas sub-mensagens `SEPARADO`.
- `editor-dados-formularios`: A geração de formulários passará a exibir todos os campos da mensagem de forma unificada, incluindo suporte a formulários inline para sub-mensagens `INLINE` e controle de presença dos valores.

## Impact

- **aresta_api/proto/croqui.proto**: Modificação para adicionar `option (aresta.mensagem_formato_ui) = SEPARADO;` em mensagens relevantes (`Pico`, `Grupo`, `Setor`, `Escalada`, etc.).
- **editor/core/protobuf_tree_model.py**: Reimplementação do modelo da árvore para expor apenas os nós de mensagens `SEPARADO`.
- **editor/views/widget_editor_dados.py**: Atualização do painel do editor para ligar a seleção de nós na árvore ao formulário completo da mensagem correspondente.
- **editor/views/protobuf_widget_factory.py**: Criação e layout de formulários unificados contendo todos os campos de uma mensagem, incluindo descrições (tooltips/comentários) e controles inline.
