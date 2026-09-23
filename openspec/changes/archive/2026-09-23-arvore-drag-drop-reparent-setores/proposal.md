## Why

Atualmente, na árvore de dados do editor, a reorganização de setores e grupos só pode ser feita item a item através das opções "Mover para Cima" e "Mover para Baixo" no menu de contexto (botão direito do mouse), o que é moroso, repetitivo e ergonomicamente ineficiente. Além disso, não existe suporte na interface para migrar um setor para dentro de um grupo, retirar um setor de um grupo para a raiz do pico, ou transferir um setor entre grupos distintos (reestruturação hierárquica), forçando o usuário a recriar o setor ou manipular manualmente arquivos Markdown e YAML.

Esta mudança introduz suporte nativo a interação de arrastar e soltar na árvore de dados, viabilizando a reordenação ágil no mesmo nível hierárquico e a migração de setores entre pais, atualizando automaticamente os nomes de arquivos conforme as convenções do projeto e resguardando o banco de dados contra colisões de arquivos existentes.

## What Changes

- **Arrastar e Soltar para Reordenação no Mesmo Nível:** Permite arrastar setores ou grupos para cima e para baixo dentro de sua coleção repetida (`pico.setores_ou_grupos` ou `grupo.setores`), reordenando os elementos através do comando existente `CmdMoverRepeated`.
- **Arrastar e Soltar para Migração Hierárquica de Setores:** Permite arrastar um setor da raiz de um Pico para dentro de um Grupo, de dentro de um Grupo para a raiz do Pico, ou entre dois Grupos distintos.
- **Biblioteca Isolada de Regras e Validações (`editor/core/migracao_setor.py`):** Criação de biblioteca autossuficiente e testável (seguindo o princípio Library-First) responsável por validar compatibilidade de movimentação, calcular novos nomes de arquivos padronizados e verificar potenciais colisões de nomes de arquivos.
- **Comando Atômico de Histórico (`CmdMigrarSetor`):** Criação de comando dedicado no histórico (`QUndoStack`) que move a mensagem `ArquivoSetor` entre os containers Protobuf e altera os metadados de caminho em uma única etapa reversível (Undo/Redo), garantindo que nenhuma mutação ocorra fora da pilha de histórico.
- **Renomeação Automática do Arquivo na Migração:**
  - Setor movido para dentro de um grupo: atualiza `caminho_novo` para o padrão `grupo_{slug_grupo}_setor_{slug_setor}.md`.
  - Setor movido para a raiz do Pico: remove o prefixo do grupo, restaurando o padrão `setor_{slug_setor}.md`.
  - Setor movido entre grupos: substitui o prefixo do grupo de origem pelo do grupo de destino.
- **Prevenção de Colisão de Arquivos:** Caso o nome proposto para o arquivo do setor colida com um arquivo já existente no disco ou agendado em memória no croqui, o movimento é abortado, um diálogo de aviso (`QMessageBox.warning`) é exibido e a árvore permanece inalterada sem poluir o histórico de Undo.
- **Validação Rigorosa de Tipos de Movimento:** Bloqueia operações inválidas pelo schema Protobuf (ex: arrastar Grupo para dentro de Grupo, arrastar Grupo para fora do Pico, arrastar sobre nós virtuais de adição ou nós expando) com feedback visual de ação proibida (`Qt.DropAction.IgnoreAction`).
- **Preservação de Foco e Seleção:** Ao concluir a soltura, o grupo de destino é expandido automaticamente e o setor recém-movido permanece selecionado no formulário lateral.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capacidade necessária; expande a especificação existente da árvore de dados -->

### Modified Capabilities
- `editor-dados-arvore`: Adiciona suporte e cenários de teste para arrastar e soltar de itens repetidos (reordenação na mesma coleção), migração hierárquica de setores (movimentação entre Pico e Grupo ou entre Grupos), renomeação reativa de arquivos via `ext_metadados_arquivo` e bloqueio com diálogo de aviso em caso de colisão de arquivos.

## Impact

- **Biblioteca de Negócios (Library-First):** Criação de `editor/core/migracao_setor.py` e sua respectiva suite de testes `editor/core/migracao_setor_test.py` com 100% de cobertura.
- **Modelos e Comandos:** Adição do comando `CmdMigrarSetor` em `editor/commands/comandos_protobuf.py` e método despachador `migrar_setor` em `CroquiController`.
- **Visualização da Árvore:** Extensão de `ProtobufTreeViewAdapter` e da visualização `QTreeView` em `editor/views/widget_editor_dados.py` para configurar flags de arraste, tipos MIME e captura/validação da soltura.
- **Diálogos e Validações:** Integração com verificação de arquivos existentes e exibição de alerta via `QMessageBox.warning` em caso de colisão de nomes de arquivos.
- **Testes:** Testes de integração em primeiro lugar (`widget_editor_dados_test.py`) seguidos por testes unitários exaustivos (`comandos_protobuf_test.py` e `migracao_setor_test.py`).
