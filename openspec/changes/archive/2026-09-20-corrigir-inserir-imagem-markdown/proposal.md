## Why

O fluxo de inserção de imagens em Markdown apresenta uma interface visual divergente e menos ergonômica que a do diálogo de adição de mapas, além de um bug crítico de persistência: ao salvar o croqui, o compilador e limpador de arquivos órfãos (`limpar_arquivos_nao_utilizados`) ignora referências de imagens presentes na maioria dos campos de texto (como `croqui.descricao`, `pico.descricao`, vias e trilhas) e deleta permanentemente os arquivos WebP do disco. Esta mudança unifica a experiência de interface e garante que nenhuma imagem legítima seja excluída ao salvar ou fechar o editor.

## What Changes

- **Unificação da UI de Inserção de Imagens**: Alinhar a interface de `DialogoInserirImagemMarkdown` ao padrão de `DialogoAdicionarMapa`, incluindo botão explícito "Selecionar Imagem..." no cabeçalho, área de Drag & Drop destacada com preview integrado, painel com metadados ricos (dimensões em pixels, peso original e comprimido em WebP), campo de nome de destino sanitizado automaticamente e validação contínua de colisões contra arquivos em disco e memória.
- **Preservação de Imagens Markdown na Limpeza de Arquivos**: Atualizar `coletar_referencias_arquivos` em `scripts/preparar_submissao_lib.py` para inspecionar recursivamente todas as descrições Markdown do croqui (`croqui.descricao`, `pico.descricao`, todas as escaladas — vias esportivas, vias móveis, boulders, vias de múltiplas enfiadas e highlines —, trilhas e pontos de interesse), impedindo o apagamento indevido de imagens referenciadas.
- **Registro no Histórico Transacional (Undo/Redo)**: Assegurar conformidade com o Princípio VII de Engenharia Aresta, registrando o armazenamento de bytes da nova imagem em memória e a inserção da tag Markdown no texto através de comandos de histórico na pilha `historico`.

## Capabilities

### New Capabilities

*(Nenhuma nova capacidade criada)*

### Modified Capabilities

- `editor-markdown-imagens`: Modificação dos requisitos do diálogo de inserção para unificar com o padrão visual e de validação de `DialogoAdicionarMapa`, exigência de rastreamento de imagens Markdown em todos os campos de texto do croqui na compilação/limpeza, e garantia de integração com a pilha de histórico `historico`.

## Impact

- **Código Afetado**:
  - `editor/views/dialogos/dialogo_inserir_imagem_markdown.py`: Reformulação da interface e reutilização/espelhamento de componentes visuais de `dialogo_adicionar_mapa.py`.
  - `editor/views/widget_editor_dados.py`: Envio e amarração do comando de inserção de imagem com a pilha de histórico e o controlador.
  - `scripts/preparar_submissao_lib.py`: Expansão de `coletar_referencias_arquivos` para extrair referências Markdown de todas as mensagens do Protobuf que possuem campos descritivos.
- **Testes**:
  - `tests/editor/views/dialogos/dialogo_inserir_imagem_markdown_test.py`
  - `tests/scripts/preparar_submissao_lib_test.py`
  - Testes de integração de fluxo de salvamento e compilação.
