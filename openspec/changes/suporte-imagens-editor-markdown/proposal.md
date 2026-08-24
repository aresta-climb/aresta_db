# Proposta: Suporte Completo de Inserção e Pré-visualização de Imagens no Editor Markdown

## Why

Atualmente, o editor Markdown no formulário de dados do Aresta Editor falha ao renderizar imagens locais (`![...](imagens/...)`) na pré-visualização em tempo real porque o caminho base do banco de dados não é resolvido pela hierarquia de componentes gráficos. Além disso, a inserção de imagens é manual e complexa: o autor precisa memorizar o caminho da pasta, saber o nome exato do arquivo, formatar a marcação Markdown manualmente e realizar a cópia e conversão de arquivos externos fora do editor.

Esta mudança corrige a resolução de imagens na pré-visualização e introduz uma experiência moderna de inserção de imagens através de biblioteca modular desacoplada (Library-First), diálogo visual com galeria e importação assistida, suporte a arrastar e soltar, colagem da área de transferência com integração ao histórico de desfazer/refazer (Undo/Redo), e autocompletar contextual.

## What Changes

- **Correção da Pré-visualização de Markdown**:
  - Resolução correta do caminho base no visualizador rico (`AutoScalingTextBrowser`) utilizando o caminho do banco de dados provido pelo modelo (`CroquiModel._caminho_db_atual`).
  - Renderização fluida de imagens `.webp`, `.png`, `.jpg` locais e ajuste dinâmico ao viewport.

- **Biblioteca Modular de Processamento e Nomenclatura (Library-First)**:
  - Criação do módulo `editor.core.imagens_markdown` com funções puras, autossuficientes e testáveis para sanitização de nomes em `snake_case`, prevenção de colisões, geração de nomes a partir de data/hora e gravação otimizada de imagens.
  - Reutilização da conversão padrão para WebP otimizado (`qualidade=85`, `area_maxima=4.194.304 px / 4 Megapixels`) com PIL/Lanczos.

- **Assistente e Diálogo de Inserção de Imagens (`DialogoInserirImagemMarkdown`)**:
  - Galeria de imagens existentes na pasta `imagens/` do croqui com filtro por nome e miniaturas.
  - Modo de Importação de novas imagens do computador ou capturas.
  - Geração automática de nome de arquivo padronizado (`snake_case` com extensão `.webp`) e campo editável para confirmação do usuário.
  - Campo opcional para Legenda gerando a marcação `![Legenda](imagens/<arquivo>.webp)`.

- **Interações Rápidas no Editor Markdown com Suporte a Histórico (Undo/Redo)**:
  - Botão de ação "Inserir Imagem" no cabeçalho do editor.
  - Arrastar e Soltar: arquivos externos acionam o diálogo de confirmação com nome sugerido e conversão automática; arquivos internos da pasta `imagens/` inserem diretamente a marcação Markdown.
  - Colar da Área de Transferência (`Ctrl+V`): interceptação de imagens do clipboard acionando o assistente de nomeação e conversão rápida para a pasta `imagens/`.
  - Inserção de texto integrada ao histórico global (`controller.alterar_primitivo` / `QUndoCommand`) para permitir desfazer e refazer a inserção da imagem.
  - Autocompletar contextual: sugestão de nomes de arquivos da pasta `imagens/` ao digitar `![` ou `imagens/`.

- **Garantia de Qualidade e Cobertura**:
  - Implementação estrita em TDD (Test-Driven Development) com 100% de cobertura de testes unitários e testes de integração em primeiro lugar.

## Capabilities

### New Capabilities
- `editor-markdown-imagens`: Biblioteca e assistente de inserção de imagens (funções modulares de nomenclatura, diálogo visual com galeria e importação, geração automática de nomes, conversão para WebP q=85 e max_area 4kk, drag & drop, paste de clipboard, integração ao histórico de undo/redo e autocompletion no editor Markdown).

### Modified Capabilities
- `editor-dados-formularios`: Atualização dos requisitos de pré-visualização de markdown para garantir a correta resolução do caminho base a partir do modelo de dados e inclusão dos novos pontos de entrada de inserção de imagens no `WidgetEditorMarkdown`.

## Impact

- `editor/core/imagens_markdown.py` e `editor/core/imagens_markdown_test.py`: Novo módulo de regras puras e utilitários de imagem/nomenclatura.
- `editor/views/widget_editor_dados.py` e `editor/views/widget_editor_dados_test.py`: Ajuste na inicialização do `WidgetEditorMarkdown` para passar o caminho do banco ao visualizador, adição de botões de ação e integração com o novo diálogo, histórico de comandos e handlers de drop/paste/autocomplete.
- `editor/views/dialogos/dialogo_inserir_imagem_markdown.py` e `editor/views/dialogos/dialogo_inserir_imagem_markdown_test.py`: Novo diálogo modal com visualização de galeria, importação de arquivos, conversão e inserção.
- Suíte de testes com 100% de cobertura e acompanhamento estrito de arquivos `_test.py`.
