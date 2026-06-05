## Why

Esta alteração é necessária para refinar a experiência do usuário e a usabilidade geral do Editor de Dados de croquis. O layout atual apresenta recuos excessivos na árvore, falta de atalhos rápidos para gerenciar coleções repetidas de dados diretamente na árvore (exigindo que o usuário role formulários extensos), renderização indesejada de campos marcados como internos/invisíveis, e formulários desalinhados onde campos pequenos ocupam toda a largura da tela. 

Estas melhorias tornarão o editor mais ergonômico, reduzindo a fadiga do usuário e acelerando o fluxo de edição de croquis.

## What Changes

- **Compactação Visual da Árvore**: Redução do recuo (indentação) horizontal padrão na árvore de dados e estilização premium das ramificações.
- **Gerenciamento de Listas na Árvore**:
  * Adição de ações de menu de contexto (clique com o botão direito) para adicionar, remover e reordenar itens repetidos.
  * Inclusão de um nó virtual interativo `+ Adicionar [Item]` no final de listas repetidas na própria árvore para inserção e seleção instantânea de novos elementos.
- **Filtragem de Visibilidade de Campos**: Ocultação automática de campos anotados com `formato_na_ui = INVISIVEL` em todas as telas de edição.
- **Layout Refinado de Formulários em Cards**:
  * Separação dos campos em cards visuais distintos para melhor distinção de escopo.
  * Constrição da largura máxima (`max-width`) para entradas numéricas e strings curtas para manter um visual equilibrado.
  * Reposicionamento contextual dos botões de presença (Adicionar/Remover) ao topo direito de cada card de campo.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `editor-dados-arvore`: Modificada para incluir a compactação de recuo, menu de contexto para edição estrutural de repeateds, e nós dinâmicos de adição rápida `+`.
- `editor-dados-formularios`: Modificada para ocultar campos invisíveis, envolver campos em cards com espaçamentos claros, constranger largura de inputs curtos e reposicionar botões de presença de forma contextual.

## Impact

- `editor/views/widget_editor_dados.py`: Modificado para estilizar a árvore com menor recuo, conectar o menu de contexto, tratar a seleção de nós virtuais `+`, e ajustar a renderização do formulário em cards com larguras máximas limitadas.
- `editor/core/protobuf_tree_model.py`: Atualizado para adicionar o nó virtual de inserção `+` no final das listas de repeateds e responder a cliques nesse nó inserindo elementos na mensagem do protobuf correspondente.
