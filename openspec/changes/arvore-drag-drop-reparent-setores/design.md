## Context

Na interface do Editor de Dados (`WidgetEditorDados`), a árvore de navegação é representada por uma `QTreeView` conectada ao modelo `ProtobufTreeViewAdapter`. A hierarquia estrutural é definida em Protobuf (`croqui.proto`):
- Um `Pico` contém uma lista repetida `setores_ou_grupos` (`repeated SetorOuGrupo`), onde cada item encapsula um `setor` (`ArquivoSetor`) ou um `grupo` (`ArquivoGrupo`).
- Um `Grupo` contém uma lista repetida `setores` (`repeated ArquivoSetor`).
- Cada `ArquivoSetor` armazena os dados do setor e metadados de arquivo (`caminho_original` e `caminho_novo` via `ext_metadados_arquivo`).

Qualquer reorganização de nós na árvore depende hoje exclusivamente do menu de contexto (clique com botão direito -> "Mover para Cima" / "Mover para Baixo"), que move itens apenas uma posição por vez através de `CmdMoverRepeated`. Não existe suporte na interface para migrar um setor para dentro de um grupo, retirá-lo de um grupo ou transferi-lo entre grupos, nem para reordenar por arraste e soltura.

Para manter a integridade arquitetural do repositório, este design adota rigorosamente os princípios de engenharia de `PRINCIPIOS.md`: nomenclatura integral em português brasileiro, isolamento de regras em biblioteca independente (**Library-First**), TDD com testes de integração prioritários, comandos atômicos no histórico e simplicidade declarativa sem abstrações prematuras.

## Goals / Non-Goals

**Goals:**
- Habilitar interação intuitiva de arrastar e soltar na árvore de dados.
- Permitir reordenação de itens repetidos dentro da mesma coleção no mesmo nível hierárquico via arraste, com indicador visual de inserção.
- Permitir migração hierárquica de setores entre o Pico e Grupos, ou entre Grupos distintos.
- Isolar a lógica de negócio em uma biblioteca autossuficiente e testável (`editor/core/migracao_setor.py` com `editor/core/migracao_setor_test.py`), conforme o princípio Library-First.
- Atualizar a extensão de metadados (`caminho_novo`) de arquivos de setor para refletir o prefixo de grupo (`grupo_{slug_grupo}_setor_{slug_setor}.md` vs `setor_{slug_setor}.md`).
- Detectar colisões de nomes de arquivos resultantes da migração, abortando a soltura e exibindo aviso (`QMessageBox.warning`) sem alterar o estado ou poluir o histórico.
- Garantir reversibilidade total (Undo/Redo) de qualquer reordenação ou migração em um único passo no `QUndoStack` via comandos de histórico (`CmdMoverRepeated` e `CmdMigrarSetor`).
- Manter o elemento movido visível, selecionado e carregado no formulário após a soltura, auto-expandindo o grupo de destino.

**Non-Goals:**
- Permitir aninhamento de grupos dentro de outros grupos (proibido pelo schema Protobuf).
- Permitir aninhamento de setores dentro de outros setores.
- Mover escaladas entre setores ou picos neste incremento (foco exclusivo em setores e grupos).
- Renomear fisicamente os arquivos no disco no instante do drop (a gravação física permanece diferida até o acionamento de `salvar_croqui()`, onde o `git mv` atua).

## Decisions

### 1. Biblioteca Dedicada de Negócios (Library-First): `editor/core/migracao_setor.py`
- **Decisão:** Criar um módulo independente contendo funções puras e autossuficientes para:
  - `validar_movimento_permitido(origem_tipo, destino_tipo, eh_sobre_item)`: avalia se a operação de soltura é válida segundo as regras do schema.
  - `calcular_novo_caminho_setor(caminho_atual, nome_setor, grupo_destino_nome=None)`: calcula o novo nome de arquivo aplicando ou removendo o prefixo `grupo_{slug_grupo}_`.
  - `verificar_colisao_nome_arquivo(novo_caminho, caminhos_existentes, caminho_atual_proprio)`: verifica duplicidade contra arquivos no disco e agendados em memória.
- **Rationale (Princípio II - Library-First & Princípio VI - Simplicidade):** Evita sobrecarregar a classe de visualização `WidgetEditorDados` (que já é extensa) com regras de negócio. O módulo é 100% testável de forma unitária sem depender do motor gráfico do Qt.
- **Alternativas consideradas:**
  - *Embutir a lógica diretamente nos métodos de evento da UI:* Rejeitado por violar frontalmente o princípio Library-First e dificultar testes unitários isolados.

### 2. Comando Atômico de Histórico: `CmdMigrarSetor`
- **Decisão:** Criar um comando dedicado `CmdMigrarSetor(model, setor_wrapper, pai_origem, campo_origem, indice_origem, pai_destino, campo_destino, indice_destino, caminho_novo, caminho_antigo)` derivado de `ComandoEditor`.
- **Rationale (Princípio VII - Edições via Comandos do Histórico):** O `PRINCIPIOS.md` determina que toda e qualquer mutação de estado a partir da UI DEVE ser realizada via comandos na pilha global de histórico (`QUndoCommand`). A migração de um setor entre listas e a alteração de seu `caminho_novo` precisam ser atômicas. Um único `Ctrl+Z` deve retornar o setor para sua lista original, no índice exato onde estava, restaurando o `caminho_novo` prévio.
- **Alternativas consideradas:**
  - *Compor múltiplos comandos separados:* Rejeitado por exigir múltiplos acionamentos de `Ctrl+Z` do usuário, podendo deixar a aplicação em estado intermediário inconsistente.

### 3. Convenção de Nomenclatura em Português Brasileiro (Princípio I)
- **Decisão:** Toda a nomenclatura interna e externa seguirá estritamente o português brasileiro:
  - Classes: `CmdMigrarSetor`, `ProtobufTreeViewAdapter`.
  - Métodos no controller: `migrar_setor`.
  - Parâmetros e variáveis: `caminho_origem`, `indice_origem`, `slug_grupo`, `eh_sobre_item`, etc.
- **Rationale:** Obediência mandatória ao Princípio I de `PRINCIPIOS.md`.

### 4. Interceptação de Eventos na `QTreeView`
- **Decisão:** Interceptar os eventos `dragEnterEvent`, `dragMoveEvent` e `dropEvent` da `tree_view` em `WidgetEditorDados`.
- **Rationale:** A implementação padrão do Qt tenta remover e reinserir linhas diretamente no modelo de visualização sem passar pelos comandos do controlador. Interceptar o evento de soltura nos permite:
  1. Extrair os índices e nós de origem e destino.
  2. Consultar a biblioteca `migracao_setor` para validar se o movimento é lícito.
  3. Verificar se há colisão de arquivos; se houver, emitir `QMessageBox.warning` e abortar (`event.ignore()`).
  4. Despachar para `self.controller.mover_repeated_...` (no caso de reordenação) ou para `self.controller.migrar_setor(...)` (no caso de migração hierárquica).
  5. Auto-expandir o grupo de destino e selecionar o setor movido.

### 5. Resolução de Conflitos por Aborto com Notificação
- **Decisão:** Se `verificar_colisao_nome_arquivo` acusar conflito, a soltura é cancelada imediatamente sem mutação no modelo ou poluição da pilha de histórico, e um aviso modal explicativo (`QMessageBox.warning`) orienta o usuário a resolver a duplicidade antes de mover.
- **Rationale:** Respeita a integridade do banco de dados, evita arquivos com nomes arbitrários e segue a postura adotada nos demais assistentes e diálogos do editor.

## Risks / Trade-offs

- **[Risco] Invalidação de referências `QModelIndex` durante reconstruções** → *Mitigação:* Localizar o nó na árvore após o comando via ID persistente (`_get_id`) e restaurar a seleção e foco de forma desacoplada.
- **[Risco] Tentativa de soltura em agrupadores ou nós virtuais de adição** → *Mitigação:* `validar_movimento_permitido` recusa terminantemente nós marcados com `is_expando` ou `eh_no_adicao`, instruindo o cursor a exibir sinal de bloqueio (`Qt.DropAction.IgnoreAction`).
- **[Risco] Queda de cobertura de testes** → *Mitigação:* Desenvolvimento rigoroso sob o ciclo TDD com 100% de cobertura unitária garantida para `migracao_setor.py` e `comandos_protobuf.py`.

## Migration Plan

Não há migração de dados de croqui necessária, pois a estrutura dos arquivos Protobuf e YAML/Markdown permanece integralmente compatível.

## Open Questions

Nenhuma questão técnica em aberto.
