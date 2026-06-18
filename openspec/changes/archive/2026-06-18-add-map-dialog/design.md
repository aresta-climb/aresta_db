## Context

Aresta Climb é focado no uso eficiente de recursos locais e controle apurado sobre o modelo de dados Protobuf, que alimenta a árvore de edição (CroquiModel). Quando um Mapa era adicionado, apenas seu registro no Protobuf era criado. A associação da imagem precisava ser feita fora do fluxo natural de edição, de forma ineficiente.

O módulo `scripts/comprimir_imagens.py` já possuía a lógica de adequação (área máx 2048*2048px e WebP com qualidade 85), e o fluxo necessitava da inserção através do sistema de Undo/Redo do Qt, já implementado robustamente via `CroquiController` e os comandos base.

## Goals / Non-Goals

**Goals:**
- Prover interface direta para adição de mapas (Dialog).
- Automatizar compressão, adequação e armazenamento de imagens dentro da pasta `imagens/` do croqui usando o mesmo padrão das outras imagens.
- Dar feedback de preview imediato.
- Gerenciar de forma unificada as mudanças na memória (Protobuf) e no sistema de arquivos local (arquivos WebP) através do `QUndoCommand`.

**Non-Goals:**
- Mudar a forma de manipulação e desenho de polígonos na imagem. Isso continuará no Editor de Mapas existente.
- Mudar formatos para algo diferente do `.webp`.
- Prover edição avançada de imagem (cortes, correções de cor).

## Decisions

### 1. Refatoração de comprimir_imagens.py
Extrair o cerne do processamento de imagens do arquivo local via `Image.open()` para uma função exposta que realize operações e retorne dados (ex: `bytes`). Assim, a lógica de compressão fica reutilizável também para operações in-memory, eliminando a dependência do disco no momento de preparar a miniatura.

### 2. QUndoCommand que armazena bytes em memória
A limitação em tamanho para área máxima de 2048*2048 pixels e WebP 85 torna seguro armazenar as cópias em memória dentro das instâncias do QUndoCommand.
- `redo()` recria a imagem em disco a partir dos bytes armazenados em memória e atuliza o Model.
- `undo()` deleta o arquivo no disco e remove o nó do Model.
Isso impede que arquivos fiquem pendentes como lixo quando o comando é desfeito.

### 3. Sugestão Automática de Nomes
A arquitetura varrerá o elemento-pai da árvore até atingir os níveis *Grupo* ou *Setor* (o que vier primeiro) para pré-preencher o nome do arquivo, ex: `grupo_x_setor_y_p0.webp`. Se o arquivo existir na pasta `imagens/`, uma exceção visual no diálogo forçará a correção pelo usuário (não sobrescreverá silenciosamente).

## Risks / Trade-offs

- **[Risco] Ocupação de RAM pelos UndoCommands**: Cada mapa inserido cria um comando que armazena um arquivo de ~200-500KB na memória até que o histórico do QUndoStack expire/seja limpo.
- **Mitigação**: O limite de qualidade (85) e de área máxima (2048*2048 pixels) evita estourar os limites, considerando os recursos das máquinas onde a ferramenta de build normalmente roda. Além do que os mapas em uma sessão normal não costumam exceder 10-20 interações do tipo "Adicionar novo" antes do salvamento da sessão.
