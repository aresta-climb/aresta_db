# Design Técnico: Suporte Completo de Inserção e Pré-visualização de Imagens no Editor Markdown

## Context

No Aresta Editor, descrições detalhadas de setores, grupos e croquis utilizam Markdown com imagens ilustrativas armazenadas na subpasta `imagens/` de cada croqui. Atualmente, o componente `WidgetEditorMarkdown` falha em resolver o caminho base para o visualizador `AutoScalingTextBrowser` devido à ausência do atributo `caminho_croqui` nos componentes gráficos ancestrais. Adicionalmente, a inserção de imagens carece de automação: o usuário precisa realizar conversões manuais e conhecer a estrutura interna de arquivos.

Este documento detalha a implementação da solução seguindo estritamente os princípios de engenharia do repositório (`PRINCIPIOS.md`): idioma 100% em português brasileiro, arquitetura Library-First, TDD com 100% de cobertura, testes de integração em primeiro lugar, simplicidade sem abstrações prematuras e rastreamento de modificações na pilha de histórico (Undo/Redo).

## Goals / Non-Goals

**Goals:**
- Implementar a biblioteca desacoplada `editor.core.imagens_markdown` com funções puras de formatação, sanitização de nomes, verificação de colisões e persistência de imagens otimizadas (Library-First).
- Corrigir a renderização em tempo real de imagens na pré-visualização do Markdown configurando o caminho base no documento Qt a partir de `self.model._caminho_db_atual`.
- Criar o diálogo modal `DialogoInserirImagemMarkdown` contendo:
  - Galeria de miniaturas das imagens presentes no croqui com busca textual.
  - Importador de novas imagens do computador ou captura com área de arrastar e soltar.
  - Geração automática de nomes de arquivo padronizados em `snake_case` com extensão `.webp` e tratamento automático de colisões de nome.
  - Otimização automática e conversão da imagem importada para WebP com `qualidade=85` e limite de área máxima de 4 Megapixels (`area_maxima=4.194.304`).
  - Campo de texto para Legenda (texto alternativo).
  - Inserção direta da tag `![Legenda](imagens/<nome>.webp)` na posição do cursor do editor.
- Habilitar atalhos e interações no editor de texto puro do Markdown (`QTextEdit`):
  - Botão de ação "Inserir Imagem" no cabeçalho do editor.
  - Arrastar e soltar de arquivos de imagem direto no editor de texto.
  - Colar imagem da área de transferência (`Ctrl+V` de prints do clipboard) abrindo o assistente com o print carregado e nome sugerido com timestamp.
  - Autocompletar contextual para imagens existentes ao digitar `![` ou `imagens/`.
- Garantir que a inserção do texto Markdown no editor passe pelo controlador (`self.controller.alterar_primitivo`), gerando comandos na pilha de histórico (`QUndoStack`) para reversibilidade completa (Undo/Redo).
- Atingir 100% de cobertura de testes unitários e de integração em todos os novos módulos e alterações.

**Non-Goals:**
- Não inclui edição gráfica ou corte (crop) avançado de imagens dentro deste diálogo (essas ferramentas pertencem à aba específica de Imagens).
- Não altera o formato de armazenamento dos dados no Protobuf/YAML (continua utilizando referências padrão `imagens/<nome>.webp` no corpo Markdown).

## Decisions

### 1. Biblioteca Modular de Imagens Markdown (`editor.core.imagens_markdown`) - Library-First
- **Decisão**: Isolar todas as funções de negócio e manipulação de arquivos em um módulo puro (`editor/core/imagens_markdown.py` acompanhado de `editor/core/imagens_markdown_test.py`), sem acoplamento direto com widgets Qt.
- **Funções da Biblioteca**:
  - `sanitizar_nome_imagem(nome_bruto: str) -> str`: Remove acentuações, espaços e caracteres especiais, convertendo para `snake_case` em minúsculas e garantindo extensão `.webp`.
  - `gerar_nome_imagem_padrao(nome_orig: str, pasta_destino: Path) -> str`: Sanitiza o nome e incrementa sufixos numéricos (`_1`, `_2`) se o arquivo já existir no diretório de destino.
  - `gerar_nome_imagem_clipboard(pasta_destino: Path) -> str`: Gera `imagem_AAAAMMDD_HHMMSS.webp` baseado na data e hora atual, tratando colisões.
  - `salvar_imagem_otimizada(fonte_imagem: Union[str, Path, bytes, Image.Image], caminho_destino: Path) -> Tuple[int, int]`: Processa via `comprimir_imagem_para_bytes_webp` (`qualidade=85`, `area_maxima=4194304`), grava no disco e retorna as dimensões finais `(largura, altura)`.
  - `formatar_tag_markdown(nome_arquivo: str, legenda: str = "") -> str`: Retorna a string formatada `![<legenda>](imagens/<nome_arquivo>)`.

### 2. Obtenção do Caminho Base a partir do `CroquiModel`
- **Decisão**: Obter `caminho_db` através de `self.model._caminho_db_atual` no `WidgetEditorMarkdown`, configurando `self.preview.document().setBaseUrl(QUrl.fromLocalFile(str(caminho_db) + "/"))`.
- **Alternativa Considerada**: Percorrer `parent()` dos widgets Qt procurando propriedades ad-hoc. Descartado por ser frágil e violar o encapsulamento MVC.

### 3. Integração com o Histórico Global de Undo/Redo
- **Decisão**: Ao confirmar a inserção da imagem no editor (seja via diálogo, drag & drop ou paste), o texto no `QTextEdit` é atualizado na posição do cursor e o valor resultante é despachado via `self.controller.alterar_primitivo(self.msg, self.field.name, valor_antigo, valor_novo)`. Isso empilha um `CmdAlterarPrimitivo` no `QUndoStack`, permitindo ao usuário desfazer a inserção com `Ctrl+Z` mantendo sincronizados os estados em memória e a árvore de dados.

### 4. Diálogo Unificado (`DialogoInserirImagemMarkdown`)
- **Decisão**: Implementar `DialogoInserirImagemMarkdown` em `editor/views/dialogos/dialogo_inserir_imagem_markdown.py` contendo:
  - **Aba "Imagens do Croqui"**: Exibe miniaturas em grade (`QListWidget` em modo de ícones) e campo de busca textual.
  - **Aba "Nova Imagem"**: Exibe área de upload/drop, preview da nova imagem, campo para nome do arquivo sugerido e botão de conversão/salvamento.
  - Campo de texto para Legenda na base do diálogo, com botões "Cancelar" e "Inserir".

### 5. Interceptação de Paste (`Ctrl+V`) e Drag & Drop no Editor
- **Decisão**: Criar classe especializada `EditorTextoMarkdown` (derivada de `QTextEdit`) dentro de `widget_editor_dados.py` para interceptar `insertFromMimeData`, `dragEnterEvent` e `dropEvent`. Se o conteúdo colado/solto contiver imagem em memória ou arquivos de imagem externos, aciona o fluxo de inserção assistida. Se for texto puro, mantém o comportamento padrão do editor.

### 6. Autocompletar Contextual Inline
- **Decisão**: Conectar um `QCompleter` ao editor de texto populado com a lista de nomes de arquivos da pasta `<caminho_db>/imagens/`, ativado contextualmente quando o cursor estiver logo após `![` ou `(imagens/`.

## Risks / Trade-offs

- **[Risco] Múltiplos formatos de imagem colados da área de transferência em diferentes sistemas operacionais** → **Mitigação**: O `QClipboard.mimeData().imageData()` do PyQt6 abstrai os formatos nativos de clipboard (Windows DIB, PNG, etc.) entregando um `QImage` padronizado que é convertido diretamente para bytes WebP.
- **[Risco] Sobrescrita acidental de imagem existente** → **Mitigação**: A função `gerar_nome_imagem_padrao` verifica a existência prévia na pasta `imagens/` e adiciona sufixos incrementais automaticamente, além de exibir um aviso se o usuário digitar manualmente um nome que já existe.
- **[Risco] Regressão na performance de renderização da árvore ao adicionar diálogo** → **Mitigação**: A leitura da pasta `imagens/` ocorre apenas no momento da abertura do diálogo ou da digitação do autocompletar, mantendo o carregamento inicial da árvore leve e instantâneo.
