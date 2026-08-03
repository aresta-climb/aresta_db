## Context

O Editor Aresta precisa de uma interface gráfica amigável para edição do `croqui.proto`. Atualmente, a manipulação do protobuf diretamente não é viável para os usuários finais. A proposta é criar um "Editor de Dados" que seja acessado via a barra lateral ("Dados") e que ofereça duas visões integradas: uma árvore de navegação de nós do protobuf à esquerda e um formulário de edição/ferramenta especializada à direita.

## Goals / Non-Goals

**Goals:**
- Implementar uma interface de árvore (`QTreeView`) suportada por um modelo de dados (`QAbstractItemModel`) que reflita a estrutura do `croqui.proto`.
- Criar a área de detalhes à direita com formulários gerados dinamicamente baseados nos tipos de campos do protobuf.
- Integrar as opções de `mime_type` para exibir interfaces especializadas (ex: quando for um tipo mapa, abrir o `WidgetEditorMapas`; quando for imagem, abrir `WidgetEditorImagens`).
- Seguir estritamente o princípio Library-First e manter o código modular e focado.

**Non-Goals:**
- Não iremos reinventar a serialização/desserialização do Protobuf; usaremos as facilidades existentes na biblioteca oficial de protobuf de Python.
- Não iremos alterar a estrutura do `croqui.proto` neste design, apenas criar a UI para percorrê-lo.

## Decisions

**1. Componente de Navegação em Árvore**
- **Decisão:** Utilizaremos `QTreeView` acoplado a uma classe customizada derivada de `QAbstractItemModel` (ex: `ProtobufTreeModel`).
- **Motivação:** Um modelo customizado garante que possamos mapear diretamente as propriedades das instâncias protobuf de forma eficiente (lazy loading) e manter a árvore em sincronia com o objeto em memória sem cópias redundantes.
- **Alternativa Considerada:** `QTreeWidget` (rejeitado por gerar muitos itens em memória, difícil de manter sincronizado com uma hierarquia aninhada dinâmica do protobuf).

**2. Roteamento da Área de Edição Direita**
- **Decisão:** Usaremos um `QStackedWidget` na porção direita do painel.
- **Motivação:** Ele permite alternar suavemente a visão entre:
  - Um `QScrollArea` genérico com formulário padrão para dados básicos.
  - O `WidgetEditorImagens` para visualização e marcação de imagens.
  - O `WidgetEditorMapas` para lidar com dados de croquis de acesso.
- Quando o usuário clicar em um item da árvore, um sinal será emitido para trocar o widget ativo da stack.

**3. Geração Dinâmica de Formulários**
- **Decisão:** Implementaremos classes fábricas para criar componentes de UI (`QLineEdit`, `QSpinBox`, `QComboBox`) lendo os `FieldDescriptor` do protobuf usando metaprogramação e reflection. Além do tipo do campo, a fábrica lerá os comentários associados ao campo (via `source_code_info` ou métodos da biblioteca) para usá-los como texto de ajuda/documentação (tooltips ou labels explicativos), e extrairá o nome de exibição diretamente do nome do campo ou das `FieldOptions`/`MessageOptions` customizadas (`ui_label` e `mime_type` definidas explicitamente no `croqui.proto`).
- **Motivação:** Permite extensibilidade fácil e garante a centralização de toda a documentação no `.proto`. Não haverá textos descritivos "hardcoded" na interface. Tipos repetidos (`repeated`) usarão um layout com listas verticais e botões '+' e '-'.

**4. Abstração de Wrappers de Arquivo**
- **Decisão:** O `ProtobufTreeModel` e as lógicas de roteamento irão interceptar os tipos `ArquivoSetor`, `ArquivoGrupo`, `ArquivoMarkdown` e `ArquivoExterno`. Para a UI, esses nós apresentarão o próprio sub-proto interno como se fosse direto, escondendo o wrapper. Na hora de serializar/modificar, o sistema garantirá que a propriedade `caminho` seja usada (referenciando arquivos `.md` ou `.yaml` externos) e nunca o `conteudo` in-line.
- **Motivação:** Mantém a UI amigável e esconde detalhes de implementação do repositório/estrutura de arquivos que não são pertinentes ao preenchimento de dados do autor, garantindo ao mesmo tempo que o sistema persista os dados da maneira correta (múltiplos arquivos ao invés de um JSON/binary gigante).

## Risks / Trade-offs

- **[Risk] Complexidade do QAbstractItemModel** → Modelos de árvore em PyQt podem ser difíceis de depurar se os índices parentais se perderem.
  **Mitigation:** Faremos testes unitários severos focando nos métodos `index()`, `parent()`, `rowCount()` e `data()`.
- **[Risk] Desempenho ao carregar nós gigantes** → Renderizar centenas de nós de vez pode travar a UI.
  **Mitigation:** `QTreeView` acoplado ao `QAbstractItemModel` já garante lazy-loading natural dos nós visíveis.
- **[Risk] Casamento de estados entre módulos independentes (Editor de Imagens/Mapas)** → Vazamento de memória ou ciclo de referência ao criar várias instâncias dos editores no QStackedWidget.
  **Mitigation:** Instanciar esses editores especializados sob demanda e destruí-los (ou reciclá-los apropriadamente) quando o nó for desselecionado.
