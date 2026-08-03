## Context

O Editor Aresta de Dados apresenta uma interface funcional, mas com oportunidade de polimento de usabilidade. A árvore de navegação possui um espaçamento horizontal excessivo que desperdiça tela. O gerenciamento de coleções repetidas exige que o usuário role formulários longos para encontrar os botões de controle de lista. Há também campos invisíveis (como marcadores de controle) sendo renderizados desnecessariamente nos formulários, e campos de entrada simples se estendem sem limites pela tela inteira.

## Goals / Non-Goals

**Goals:**
- Compactar a árvore de navegação para economizar espaço horizontal.
- Facilitar a criação, remoção e ordenação de coleções repetidas através de cliques rápidos na árvore (via nó virtual de adição `+` e menu de contexto).
- Ocultar campos marcados com `INVISIVEL` para limpar os formulários.
- Melhorar a clareza e separação dos campos no formulário usando cards com larguras controladas para inputs menores.

**Non-Goals:**
- Alterar as visões de Editor de Imagens ou Editor de Mapas.
- Modificar o fluxo de compilação ou deploy externo de croquis.

## Decisions

### 1. Indentação da Árvore (`QTreeView`)
- **Decisão**: Configurar `self.tree_view.setIndentation(12)` e aplicar estilos QSS personalizados na moldura da árvore para tornar as ramificações mais limpas.
- **Alternativas consideradas**: Desenhar recuos personalizados em um `QStyledItemDelegate`. **Rejeitada** devido ao overhead de renderização desnecessário quando o ajuste de indentação nativo do `QTreeView` atende perfeitamente.

### 2. Gestão de Coleções Diretamente na Árvore
- **Decisão**: 
  1. Estender `ProtobufNode` para suportar um tipo de nó de inserção (`eh_no_adicao = True`). No final de cada coleção no loop de `_populate_children` do `ProtobufTreeModel`, inserir um nó virtual com nome `+ Adicionar [Tipo]`.
  2. Em `WidgetEditorDados._on_tree_selection_changed`, ao detectar a seleção de um nó de inserção, invocar o método de adição, reconstruir a árvore, expandir até o novo item e selecioná-lo automaticamente.
  3. Adicionar menu de contexto na árvore (`customContextMenuRequested`):
     - Nós Expando: **Adicionar [Item]**.
     - Nós Filho: **Excluir Item**, **Mover para Cima**, **Mover para Baixo** (reordenando o repeated no Protobuf e disparando refresh do modelo).
- **Alternativas consideradas**: Apenas menu de contexto. **Rejeitada** pois o nó virtual `+` na árvore é muito mais amigável e visível (design-driven).

### 3. Filtro de Campos com Visibilidade Invisível
- **Decisão**: Durante as rotinas de renderização de campos (`_render_message_fields` e `_render_oneof`), inspecionar as opções do descriptor do campo. Se `formato_na_ui` possuir o valor `INVISIVEL` (3), o campo correspondente não será criado no layout.
- **Justificativa**: Garante que o editor oculte dados de controle interno definidos no protobuf.

### 4. Layout de Formulário em Cards e Controle de Largura
- **Decisão**: 
  1. Envolver cada campo renderizado em um `QFrame` com estilo de card (borda fina `#e0e0e0`, fundo `#ffffff` e cantos arredondados de `4px`).
  2. Ajustar `setMaximumWidth` nos widgets de edição primitivos:
     - `QLineEdit` (campos curtos como nome, sigla): `450px`.
     - `QSpinBox` / `QDoubleSpinBox` (números): `150px`.
     - `QComboBox` / `QCheckBox`: `200px` ou largura de conteúdo.
     - Markdown: Manter expandido para largura total do painel de dados.
  3. Reposicionar botões de presença (Adicionar / Remover) do campo: em vez de ficarem perdidos abaixo do input, serão posicionados no canto superior direito do card do campo.
- **Alternativas consideradas**: Usar `QFormLayout` padrão. **Rejeitada** pois o layout em cards com agrupamentos e títulos integrados oferece melhor legibilidade e distinção para formulários ricos que misturam primitivos e sub-mensagens.

## Risks / Trade-offs

- **[Risco]** O nó virtual `+` de adição não possui mensagem protobuf associada, o que pode quebrar funções que esperam `node.message` preenchido.
  - **Mitigação**: O nó virtual terá `node.message = None` e `node.eh_no_adicao = True`. Atualizar o método `load_node` e os seletores para ignorar nós onde `eh_no_adicao` for verdadeiro, ou tratar seu clique para disparar o comando de adição e redirecionar a seleção.
- **[Risco]** Reconstruir a árvore (`rebuild_tree`) ao adicionar ou remover itens faz com que a árvore colapse, perdendo a posição atual do usuário.
  - **Mitigação**: Antes de atualizar a árvore, salvar o estado de expansão de índices e restaurá-los após o reset do modelo. Na inserção, expandir explicitamente até o novo índice criado.
- **[Risco]** Mover itens para cima/baixo na árvore pode perder a referência de seleção.
  - **Mitigação**: Disparar `layoutChanged` do modelo de árvore após a reordenação em RAM e re-selecionar o índice correspondente no modelo.
