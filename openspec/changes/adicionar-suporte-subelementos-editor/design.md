## Context

No editor Aresta, o `Croqui` é uma estrutura hierárquica Protobuf composta por entidades estruturais principais (`Pico`, `Grupo`, `Setor`, `Escalada`, `Botao`). A navegação principal entre essas entidades ocorre através da árvore lateral (`QTreeView` alimentada pelo `ProtobufTreeViewAdapter`), enquanto a edição de propriedades escalares ocorre no formulário da direita (`WidgetFormularioPadrao`).

Atualmente, `_collect_eligible_under_message` em `tree_view_adapter.py` só coleta campos repetidos se `len(repeated_container) > 0`. Consequentemente, quando uma mensagem pai é recém-criada (por exemplo, um novo croqui que possui apenas o `Pico` base sem setores), o nó expando de `Setores ou grupos` não é gerado, impedindo a criação de setores ou grupos. O mesmo bloqueio acontece para `Escaladas` sob um novo `Setor`, `Setores` sob um novo `Grupo`, ou `Botões` e `Picos` adicionais sob o `Croqui`.

## Goals / Non-Goals

**Goals:**
- Garantir que qualquer coleção repetida de mensagens elegíveis para a árvore (`SEPARADO`, `ONEOF`, `ONEOF_CONTEUDO`) gere seu nó expando e nó virtual `+ Adicionar [Tipo]` na árvore, mesmo quando a lista estiver vazia.
- Permitir adição intuitiva de elementos que são uniões (`ONEOF`), como `SetorOuGrupo` (Setor vs Grupo) e `Escalada` (Via Esportiva, Boulder, Via Móvel, etc.), através de diálogo de seleção unificado acionado pelo nó virtual.
- Adicionar suporte a ações contextuais de clique com o botão direito nos nós estruturais da árvore para adicionar sub-elementos diretamente no elemento selecionado.
- Adicionar cartões de atalho contextual no rodapé dos formulários da direita para permitir adição de sub-elementos com um clique diretamente a partir da visualização da entidade pai.
- Assegurar que toda e qualquer mutação de adição seja executada estritamente via `CroquiController` / `QUndoCommand`, preservando total suporte a desfazer/refazer (Undo/Redo).
- Manter o foco automático e expansão da árvore no item recém-adicionado, tanto ao adicionar via árvore quanto via cartão de rodapé.
- Atingir 100% de cobertura de testes unitários e de integração, com código 100% em português brasileiro.

**Non-Goals:**
- Não alterar os esquemas `.proto` existentes em `aresta_api` nem as regras de compilação do banco de dados.
- Não alterar a lógica de serialização em disco ou o funcionamento do Shadow State (`MetadadosArquivoNoEditor`), que já oferecem suporte completo.
- Não criar editores inline de árvores complexas dentro do formulário; a edição de cada sub-entidade continua ocorrendo na sua própria página de formulário ao ser selecionada na árvore.

## Conformidade com PRINCIPIOS.md

### I. Tudo em Português
Todas as novas funções, métodos internos, variáveis locais, sinais e comentários de código serão estritamente nomeados em português brasileiro (ex: `_renderizar_cartao_subelementos`, `_executar_adicionar_item_contexto`, `campos_elegiveis`, `total_itens`).

### II & VI. Simplicidade, Anti-Abstração e Library-First
Não serão criadas fábricas genéricas, hierarquias de herança ou classes abstratas desnecessárias. Os cartões de rodapé serão compostos diretamente por widgets nativos do PyQt6 (`QFrame`, `QVBoxLayout`, `QHBoxLayout`, `QLabel`, `QPushButton`), mantendo o código declarativo, limpo e direto.

### III, IV & V. TDD, Testes de Integração Primeiro e 100% de Cobertura
O ciclo **Red-Green-Refactor** será estritamente aplicado. Primeiro serão desenvolvidos testes de integração de ponta a ponta que inicialmente falham (Red), seguidos pelos testes unitários específicos nos arquivos `tree_view_adapter_test.py` e `widget_editor_dados_test.py`. A implementação será realizada para fazê-los passar (Green) e então o código será refatorado (Refactor) com garantia de 100% de cobertura.

### VII. Edições de Estado via Comandos do Histórico (Undo/Redo)
Toda adição acionada (seja pelo nó virtual da árvore, pelo menu de contexto de botão direito ou pelo botão do cartão de rodapé) chamará exclusivamente o método `self.controller.adicionar_repeated()`, o qual empilha um `CmdAdicionarItemRepeated` na pilha `QUndoStack` do modelo. Nenhuma mutação direta nos objetos Protobuf ocorrerá fora do fluxo de comandos do histórico.

## Decisions

### Decisão 1: Detecção de elegibilidade baseada no Message Descriptor do campo
- **Abordagem**: Em `tree_view_adapter.py`, `_collect_eligible_under_message` inspeciona `field.message_type` do Protobuf. Se o descritor for elegível (`SEPARADO`, `ONEOF`, `ONEOF_CONTEUDO`), o campo repetido é incluído nos resultados independentemente do tamanho atual do container (`len(repeated_container) == 0`).
- **Alternativa rejeitada**: Listar explicitamente nomes de campos em um dicionário estático no código Python. Rejeitada porque viola o princípio declarativo guiado pelo Protobuf já estabelecido no projeto.

### Decisão 2: Diálogo modal padrão para ONEOFs no nó virtual único
- **Abordagem**: Manter um único nó virtual por coleção na árvore (ex: `+ Adicionar Setor ou Grupo` ou `+ Adicionar Escalada`). Ao ser acionado, se a mensagem for um ONEOF sem padrão (`oneof_default`), o método `inicializar_oneofs` exibe um `QInputDialog` com as opções disponíveis.
- **Alternativa rejeitada**: Criar múltiplos nós virtuais para cada subtipo na árvore (ex: `+ Adicionar Setor` e `+ Adicionar Grupo` como irmãos). Rejeitada para manter a árvore limpa, compacta e alinhada à preferência do usuário.

### Decisão 3: Menu de contexto estendido em nós estruturais
- **Abordagem**: Em `WidgetEditorDados._mostrar_menu_contexto_arvore`, ao clicar em um nó que representa uma mensagem estrutural (`Croqui`, `Pico`, `Grupo`, `Setor`), identificar seus campos repetidos elegíveis e adicionar ações como `Adicionar Setor ou Grupo...`, `Adicionar Escalada...`, `Adicionar Botão...`. As ações despacham a criação via controller e histórico de undo/redo.
- **Alternativa considerada**: Ter menus de contexto apenas nos nós expandos. Rejeitada porque o usuário frequentemente clica com o botão direito diretamente no item pai (ex: no Pico) para gerenciar seus filhos.

### Decisão 4: Cartão de sub-elementos no rodapé dos formulários
- **Abordagem**: Em `WidgetFormularioPadrao._render_message_fields`, para mensagens que contêm sub-mensagens elegíveis para a árvore (`Croqui`, `Pico`, `Grupo`, `Setor`, `ViaMultiplasEnfiadas`), renderizar um card no final do formulário (`QFrame` estilizado) com o nome da coleção, o contador de itens e um botão `[ + Adicionar <Tipo> ]`. Ao ser clicado, despacha a adição via `controller.adicionar_repeated`, que notifica o model via undo/redo, atualiza a árvore e navega até o novo elemento.

## Risks / Trade-offs

- **[Risco] Reconstrução da árvore perder o nó recém-adicionado**: Quando um item é adicionado a uma coleção que anteriormente estava vazia, a árvore precisa garantir que o nó expando esteja expandido e o novo item selecionado.
  - *Mitigação*: Usar a rotina existente `_localizar_no_por_indice` e emitir os sinais do model (`repeated_adicionado`) para que `find_expando_index` encontre o expando agora existente.
- **[Risco] Poluição visual no formulário**: Adicionar muitos cards de rodapé pode aumentar a altura do formulário.
  - *Mitigação*: Cards compactos e limpos no padrão de design do Aresta, apenas para sub-coleções diretas relevantes da mensagem atual.
