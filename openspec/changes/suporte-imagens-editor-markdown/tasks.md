## 1. Correção da Resolução de Caminhos na Pré-visualização do Markdown

- [x] 1.1 Criar testes de integração em `editor/views/widget_editor_dados_test.py` verificando a configuração do `baseUrl` no visualizador a partir de `self.model._caminho_db_atual` e carregamento de imagens locais
- [x] 1.2 Atualizar `WidgetEditorMarkdown` em `editor/views/widget_editor_dados.py` para extrair o caminho do banco diretamente de `self.model._caminho_db_atual` e configurar `setBaseUrl`

## 2. Biblioteca Modular de Imagens Markdown (Library-First)

- [x] 2.1 Criar testes unitários em `editor/core/imagens_markdown_test.py` para funções de sanitização de nomes, prevenção de colisões de arquivos, nomes de timestamp para capturas e formatação de tags
- [x] 2.2 Implementar as funções `sanitizar_nome_imagem`, `gerar_nome_imagem_padrao`, `gerar_nome_imagem_clipboard` e `formatar_tag_markdown` em `editor/core/imagens_markdown.py`
- [x] 2.3 Criar testes unitários em `editor/core/imagens_markdown_test.py` para a função `salvar_imagem_otimizada` (conversão para WebP `qualidade=85`, `area_maxima=4194304`)
- [x] 2.4 Implementar `salvar_imagem_otimizada` em `editor/core/imagens_markdown.py` integrando com `comprimir_imagem_para_bytes_webp`

## 3. Diálogo de Inserção de Imagens no Markdown

- [x] 3.1 Criar testes de integração e de interface em `editor/views/dialogos/dialogo_inserir_imagem_markdown_test.py` para o diálogo `DialogoInserirImagemMarkdown` (listagem de imagens existentes, busca textual e seleção de imagem com/sem legenda)
- [x] 3.2 Implementar a visualização de Galeria de imagens existentes e campo de legenda em `editor/views/dialogos/dialogo_inserir_imagem_markdown.py`
- [x] 3.3 Criar testes em `editor/views/dialogos/dialogo_inserir_imagem_markdown_test.py` para a aba/modo de importação de novas imagens (seleção de arquivos do computador, drag & drop na área de drop, pré-visualização, sugestão/edição de nome e persistência otimizada)
- [x] 3.4 Implementar a aba/modo de Importação em `editor/views/dialogos/dialogo_inserir_imagem_markdown.py`

## 4. Ações Rápidas no Editor Markdown com Suporte a Histórico (Undo/Redo)

- [x] 4.1 Criar testes em `editor/views/widget_editor_dados_test.py` para a inserção de imagem via botão da interface e verificação do registro na pilha de histórico (`QUndoStack`)
- [x] 4.2 Adicionar botão "Inserir Imagem" no cabeçalho do `WidgetEditorMarkdown` e conectar ao diálogo com despacho de alteração via `self.controller.alterar_primitivo`
- [x] 4.3 Criar testes em `editor/views/widget_editor_dados_test.py` para arrastar e soltar (Drag & Drop) de arquivos de imagem no editor
- [x] 4.4 Implementar tratamento de `dragEnterEvent` e `dropEvent` no editor de texto do `WidgetEditorMarkdown`
- [x] 4.5 Criar testes em `editor/views/widget_editor_dados_test.py` para colagem (`Ctrl+V`) de imagens da área de transferência
- [x] 4.6 Implementar interceptação de colar imagens da área de transferência no editor de texto do `WidgetEditorMarkdown`
- [x] 4.7 Criar testes e implementar autocompletar contextual (`QCompleter`) de imagens da pasta `imagens/` no editor de texto

## 5. Validação de Cobertura e Regressão

- [x] 5.1 Executar a suíte de testes com cobertura (`pytest --cov=editor`) garantindo 100% de cobertura nos novos módulos e alterações
- [x] 5.2 Executar testes de integração do editor e verificar ausência de regressões
