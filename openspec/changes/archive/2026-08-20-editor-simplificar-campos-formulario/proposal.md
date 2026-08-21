## Why

Atualmente, o editor de dados exibe botões contextuais de `[Adicionar]` e `[Remover]` em cada card de campo individual para lidar com a semântica de presença de campos do Protobuf (ausente, presente vazio, presente com valor). Isso introduz poluição visual excessiva, fricção de interação (o usuário é obrigado a clicar em "Adicionar" antes de digitar qualquer dado) e prejudica a experiência de uso.

Esta proposta simplifica a interface do editor em total conformidade com os `PRINCIPIOS.md`: todos os campos passam a ser exibidos diretamente para preenchimento, e a presença no Protobuf e YAML é inferida pela regra "Vazio = Ausente".

## What Changes

- **Remoção dos botões de Adicionar e Remover nos cards individuais**: Elimina os botões `[Adicionar]` e `[Remover]` no cabeçalho dos campos primitivos e submensagens inline.
- **Regra "Vazio = Ausente" (Empty = Absent)**:
  - **Strings e Markdown**: Campo vazio (`text.strip() == ""`) limpa a presença do campo no Protobuf (`ClearField`) e o omite na serialização YAML; ao digitar, o campo passa a estar presente.
  - **Pontos Flutuantes (Floats/Doubles/Coordenadas GPS)**: Editados via `QLineEdit` com validador numérico de precisão livre. Se vazio, o campo é omitido.
  - **Inteiros (`int32`, `sint32`, `uint32`)**: Editados via `QSpinBox` com suporte a estado nulo ("Não definido"), diferenciando ausência de `0`.
  - **Submensagens Inline (ex: `Coordenada`)**: Exibem diretamente seus campos filhos (Latitude, Longitude). Se ambos estiverem vazios, a submensagem pai é limpa via `ClearField`.
- **Booleanos Tri-state via QComboBox e Opções Protobuf**:
  - Campos booleanos passam a ser editados como um dropdown de 3 estados: `[Não informado (ausente), Sim (True), Não (False)]`.
  - Adição de extensões em `croqui.proto` (`booleano_texto_indefinido`, `booleano_texto_sim`, `booleano_texto_nao`) para customização semântica por campo.
- **Manutenção de Botões em Listas (`repeated`)**: Controles de adicionar e remover itens em listas continuam existindo normalmente devido à sua cardinalidade dinâmica.
- **Edição de Estado via Comandos do Histórico (Princípio VII)**: Toda limpeza (`ClearField`) e atribuição de valor é realizada exclusivamente através de `QUndoCommand` na pilha global de histórico, garantindo 100% de reversibilidade (Desfazer/Refazer).

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability raiz, apenas refinamento das existentes -->

### Modified Capabilities
- `editor-dados-formularios`: Remove a exigência de botões de presença contextuais (Adicionar/Remover) nos cards de campos, estabelece a renderização sempre visível de campos com limpeza automática ao esvaziar, introduz suporte a `QComboBox` tri-state para booleanos, `QLineEdit` para floats/coordenadas e `QSpinBox` nulo para inteiros, mantendo despacho via comandos de histórico.
- `protobuf-editor-metadata`: Adiciona opções de campo (`booleano_texto_indefinido`, `booleano_texto_sim`, `booleano_texto_nao`) para personalizar os rótulos dos estados booleanos na UI.

## Impact

- **Código Afetado**:
  - `aresta_api/proto/croqui.proto` (definição das novas FieldOptions) e código gerado `croqui_pb2.py`.
  - `editor/views/protobuf_widget_factory.py` e `protobuf_widget_factory_test.py` (criação e configuração de widgets especializados por tipo).
  - `editor/commands/comandos_protobuf.py` e `comandos_protobuf_test.py` (suporte transacional a `ClearField` e restauração de presença no histórico).
  - `editor/views/widget_editor_dados.py` e `widget_editor_dados_test.py` (remoção dos botões de presença, novos bindings de esvaziamento/presença, renderização direta de submensagens).
  - `editor/views/widget_editor_dados_historico_test.py` (testes de integração de Undo/Redo com campos esvaziados).
- **Aderência aos Princípios**:
  - 100% em português brasileiro (código, testes, documentação).
  - Testes de integração em primeiro lugar, seguidos de TDD rigoroso (Red-Green-Refactor) com 100% de cobertura de testes unitários.
- **Dependências**: Nenhuma nova dependência externa.
