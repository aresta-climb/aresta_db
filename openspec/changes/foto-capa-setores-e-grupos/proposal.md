# Proposta: Foto de Capa para Setores e Grupos

## Motivação (Why)

Atualmente, fotos representativas e panorâmicas de setores e grupos de escalada estão embutidas no meio ou no início do texto livre em Markdown. Isso faz com que imagens bonitas de apresentação fiquem "empurradas" para baixo no corpo da página no aplicativo móvel e no editor, sem destaque visual adequado. Além disso, não há no schema Protobuf (`croqui.proto`) um campo estruturado para foto de capa dessas entidades (diferente do `Croqui`, que já possui o `caminho_thumbnail`).

A inclusão do campo `caminho_imagem_capa` nos elementos `Setor` e `Grupo`, com exibição priorizada no topo da interface antes do nome, e a migração das fotos já existentes nos arquivos Markdown trazem uma evolução estética imediata sem quebrar a compatibilidade com versões antigas do aplicativo.

## O Que Muda (What Changes)

- **Schema Protobuf (`croqui.proto`):**
  - Adição do campo `string caminho_imagem_capa = 5` nas mensagens `Setor` e `Grupo`, com anotações `(aresta.formato_na_ui) = IMAGEM`, `(aresta.tipo_conteudo) = CAMINHO` e `(aresta.mime_type) = "image/webp"`.
  - Re-geração dos stubs de código Python e Dart via `python aresta_api/build.py`.

- **Orçamento de Imagem (1 MP):**
  - Configuração do limite de resolução para 1.000.000 pixels (`AREA_MAXIMA_ESCALADA` @ Q85) para fotos de capa, garantindo arquivos leves (~70 KB a 130 KB em WebP) sem consumo desnecessário de espaço no download offline.

- **Interface do Editor Desktop (`editor/`):**
  - O formulário de edição (`widget_editor_dados.py`) passa a renderizar `caminho_imagem_capa` no topo absoluto da tela de `Setor` e `Grupo`, antes do campo `nome`.
  - Reúso integral de `WidgetCampoImagem`, configurado com o teto de 1 MP e controle de Undo/Redo no histórico.
  - Registro de `caminho_imagem_capa` em `editor/core/imagens_croqui.py` para gerenciamento de buffer em RAM e detecção de imagens órfãs.

- **Pipeline de Deploy e Compilação (`scripts/`):**
  - Inclusão de `caminho_imagem_capa` na coleta de arquivos externos e checksums em `preparar_submissao_lib.py` e `deploy_generated.py`.

- **Script Utilitário de Migração Ampla (`scripts/extrair_capas_markdown.py`):**
  - Criação de script utilitário para varrer os arquivos `.md` em `database/`, detectar imagens de destaque no Markdown, promovê-las ao campo `caminho_imagem_capa` no Frontmatter YAML (otimizadas a 1 MP) e remover a tag `![alt](caminho)` do corpo textual, permitindo revisão manual no editor.

## Capacidades (Capabilities)

### Novas Capacidades
- `extracao-capas-markdown`: Script utilitário e regras de extração e promoção de imagens de capa a partir de arquivos Markdown existentes para o frontmatter YAML de setores e grupos.

### Capacidades Modificadas
- `editor-campo-imagem`: Suporte a limite de resolução customizado (1 MP para capas), priorização de exibição no topo dos formulários de dados e suporte a `caminho_imagem_capa` em `Setor` e `Grupo`.

## Impacto (Impact)

- **Compatibilidade:** Totalmente retrocompatível. Versões legadas do aplicativo móvel simplesmente ignorarão o novo campo do Protobuf e continuarão funcionando normalmente.
- **Armazenamento:** Impacto desprezível no tamanho final dos pacotes compilados offline devido à compressão estrita de 1 MP em WebP.
- **Arquivos Afetados:**
  - `aresta_api/proto/croqui.proto`
  - `editor/core/imagens_croqui.py`
  - `editor/views/widget_editor_dados.py`
  - `editor/views/protobuf_widget_factory.py`
  - `editor/views/widget_campo_imagem.py`
  - `scripts/preparar_submissao_lib.py`
  - `scripts/deploy_generated.py`
  - Novo: `scripts/extrair_capas_markdown.py` e `scripts/extrair_capas_markdown_test.py`
