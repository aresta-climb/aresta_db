## Why

Atualmente, a edição de seções textuais (botões) no editor exibe o cabeçalho YAML frontmatter e licenças SPDX no editor Markdown bruto, poluindo a visualização e gerando risco de corrupção acidental do cabeçalho. Além disso, o processo de compilação em `deploy_generated.py` ignora silenciosamente imagens inexistentes referenciadas em mapas e markdowns, e eventuais correções automáticas feitas no disco pela rotina de compilação (como migração de caminhos `raw_pdf_contents` para `imagens/`) não são refletidas na memória do editor, causando sobrescrita de dados antigos em salvamentos subsequentes.

## What Changes

- **Ocultação Transparente do Frontmatter no Editor**:
  - `WidgetEditorMarkdown` e `CroquiModel` passam a isolar o YAML frontmatter (cabeçalhos SPDX/ODbL e metadados) do corpo do Markdown.
  - O editor de texto bruto (`EditorTextoMarkdown`) e o preview passam a exibir e editar estritamente o conteúdo Markdown limpo.
  - Ao salvar no disco, o frontmatter original é automaticamente recomposto no topo do arquivo `.md`.
- **Aviso de Imagens Ausentes no Deploy**:
  - `scripts/deploy_generated.py` inspeciona recursivamente todas as referências de imagens no croqui compilado (`caminho_imagem_mapa`, `caminho_thumbnail` e marcações Markdown `![...](...)`).
  - Emite avisos (`Warning`) no console para qualquer imagem local que não for encontrada na pasta do croqui.
- **Recarregamento Condicional do Database no Editor**:
  - `scripts/preparar_submissao_lib.py` (`corrigir_database`) e `scripts/deploy_generated.py` passam a reportar se alguma modificação foi realizada nos arquivos de entrada da pasta `database/`.
  - O editor (`_on_salvar_sucesso`) só executa a recarga dos dados do disco se o compilador tiver de fato modificado o `database/`, mantendo a performance máxima e evitando recargas desnecessárias em salvamentos comuns.

## Capabilities

### New Capabilities
- `validacao-referencias-imagens`: Validação e emissão de alertas durante o deploy para imagens referenciadas em mapas, miniaturas e textos Markdown que não existem no disco.

### Modified Capabilities
- `editor-markdown-imagens`: Ocultação do cabeçalho YAML frontmatter na edição raw de seções markdown, mantendo sua preservação e recomposição em disco.
- `salvamento-assincrono`: Sincronização condicional e recarregamento dos dados do croqui na interface quando o processo de salvamento/deploy alterar arquivos na pasta `database/`.

## Impact

- **Código Afetado**:
  - `editor/models/croqui_model.py`: Separação e preservação do frontmatter de `ArquivoMarkdown`.
  - `editor/views/widget_editor_dados.py`: Edição pura do corpo Markdown sem hacks de preview.
  - `scripts/preparar_submissao_lib.py`: Retorno de indicador de modificação em `corrigir_database`.
  - `scripts/deploy_generated.py`: Verificação de imagens inexistentes e propagação de modificação no database.
  - `editor/core/workspace.py` e `editor/core/worker.py`: Propagação do sinal de database modificado na tarefa de salvamento.
  - `editor/legacy_views/area_principal.py`: Recarregamento condicional dos dados do disco ao salvar com sucesso.
- **Dependências e APIs**: Nenhuma nova dependência externa necessária.
