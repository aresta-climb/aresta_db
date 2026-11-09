# Spec Delta

## ADDED Requirements

### Requirement: Migração de Escaladas entre Setores por Arrastar e Soltar
O sistema SHALL permitir a migração de itens `Escalada` entre diferentes `Setor` na árvore de dados via arrastar e soltar (drag-and-drop), suportando soltura entre escaladas do setor de destino, antes de `+ Adicionar Escalada`, sobre o nó agrupador `Escaladas` ou diretamente sobre o nó `Setor`. A operação SHALL ser executada atomicamente no histórico de Undo/Redo preservando o `uid` e imagens em RAM, expandindo o destino e selecionando a escalada migrada.

#### Scenario: Mover escalada de um setor para posição específica entre escaladas de outro setor
- **WHEN** o usuário arrasta uma `Escalada` de um `Setor` de origem e a solta entre duas escaladas (ou antes de `+ Adicionar Escalada`) de um `Setor` de destino distinto
- **THEN** o sistema SHALL remover a escalada do setor de origem e inseri-la no índice correspondente do setor de destino em um único comando de histórico (`CmdMacro`), preservando seu `uid` e selecionando a escalada na nova posição.

#### Scenario: Mover escalada soltando diretamente sobre um nó de Setor ou agrupador Escaladas
- **WHEN** o usuário arrasta uma `Escalada` de um `Setor` de origem e a solta diretamente sobre o nó de outro `Setor` ou sobre o seu nó agrupador `Escaladas`
- **THEN** o sistema SHALL inserir a escalada ao final da lista `escaladas` do setor de destino via histórico de Undo/Redo, expandir o setor de destino e selecionar a escalada migrada.

#### Scenario: Desfazer e refazer migração de escalada entre setores
- **WHEN** o usuário aciona Desfazer (Undo) após migrar uma escalada entre setores via arrastar e soltar
- **THEN** o sistema SHALL remover a escalada do setor de destino e restaurá-la ao setor e índice originais, mantendo a árvore sincronizada.

## MODIFIED Requirements

### Requirement: Validação Visual de Operações Inválidas de Soltura
O sistema SHALL validar as regras do schema Protobuf durante o arraste e exibir o cursor de ação proibida (`Qt.DropAction.IgnoreAction`) ao passar sobre alvos ilegais.
São estritamente proibidas as seguintes operações:
- Soltar um `Grupo` sobre outro `Grupo` ou sobre um `Setor`.
- Soltar um `Setor` sobre outro `Setor` (como filho).
- Soltar uma `Escalada` sobre um `Grupo`, `Pico`, `Botao` ou entre itens de coleções que não sejam `escaladas`.
- Arrastar nós virtuais de adição (`+ Adicionar ...`) ou nós agrupadores (expandos), ou soltar itens sobre expandos/nós de adição incompatíveis com o tipo de origem.

#### Scenario: Bloqueio visual ao arrastar Grupo sobre outro Grupo
- **WHEN** o usuário tenta arrastar um Grupo sobre outro nó de Grupo
- **THEN** o sistema SHALL indicar ação proibida e ignorar a soltura.

#### Scenario: Bloqueio visual ao arrastar Escalada sobre Grupo ou entre Setores
- **WHEN** o usuário tenta arrastar uma Escalada sobre um nó de Grupo ou entre dois Setores na lista do Pico
- **THEN** o sistema SHALL indicar ação proibida e ignorar a soltura.
