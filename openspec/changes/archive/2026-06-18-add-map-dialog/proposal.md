## Why

A experiência atual de adicionar um novo mapa a um setor no editor de croquis está desconectada do processo natural. Atualmente, o usuário clica em "Adicionar Item", o que apenas cria uma estrutura de dados vazia para o Mapa no CroquiModel. Para de fato adicionar a imagem do mapa, o usuário precisaria navegar por outras interfaces e arrumar o arquivo manualmente. Isso quebra o fluxo de trabalho e torna a adição de mapas uma tarefa confusa e propensa a erros, como criar itens fantasma sem imagens.

## What Changes

- Quando o usuário clicar em "Adicionar Item" no campo de Mapas, um novo diálogo (`DialogoAdicionarMapa`) será aberto em vez de apenas criar o item vazio.
- O diálogo permitirá selecionar um arquivo de imagem (via clique ou drag-and-drop).
- Será gerado um nome de arquivo automático baseado na hierarquia (ex: `grupo_<nome_grupo>_setor_<nome_setor>_p0.webp`), editável.
- Se a imagem com o mesmo nome já existir, mostrar erro.
- A imagem selecionada terá preview.
- Após confirmar, a imagem será comprimida na memória (área máxima de 2048*2048 pixels e WebP com qualidade 85, reaproveitando a lógica base de `scripts/comprimir_imagens.py` que será refatorado).
- Tudo será envelopado num `QUndoCommand` (salvando os bytes do WebP na memória), que adicionará os dados no modelo e criará o arquivo em disco no `redo()`, e apagará o arquivo e do modelo no `undo()`.

## Capabilities

### New Capabilities
- `dialogo-adicionar-mapa`: Interface visual e fluxo otimizado para adicionar mapas e tratar a compressão e nomenclatura no momento da criação do item.

### Modified Capabilities
- Nenhuma.

## Impact

- `editor/views/widget_editor_dados.py` será modificado para interceptar a adição do Mapa.
- `scripts/comprimir_imagens.py` será refatorado para extrair a lógica puramente em memória (`comprimir_imagem_para_bytes`).
- `editor/controllers/croqui_controller.py` e `editor/commands/comandos_mapas.py` (novo) para orquestrar o `QUndoCommand` com operações em disco de forma segura.
