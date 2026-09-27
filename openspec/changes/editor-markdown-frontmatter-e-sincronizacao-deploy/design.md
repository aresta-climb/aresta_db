## Context

Veja motivação detalhada em `proposal.md`.

Atualmente, `CroquiModel.carregar_arquivos_externos` lê os arquivos `.md` associados a botões em sua totalidade (incluindo o frontmatter YAML delimitado por `---`) e atribui o texto bruto à propriedade `md.conteudo` do Protobuf. Na interface gráfica, `WidgetEditorMarkdown` exibe esse texto integral no campo de edição bruta, exigindo um tratamento artificial (`split("---")`) para a pré-visualização.

Paralelamente, a rotina de compilação em `deploy_generated.py` executa `corrigir_database`, que pode migrar caminhos de imagens em arquivos `.yaml` e `.md` na pasta `database/`. Como o editor não é notificado dessas alterações no disco e não recarrega o `CroquiModel`, o estado em memória permanece defasado. Além disso, nenhuma validação alerta desenvolvedores caso imagens referenciadas em mapas ou textos Markdown não existam no repositório.

## Goals / Non-Goals

**Goals:**
- Isolar o frontmatter na edição de botões: o editor bruto e o preview devem operar exclusivamente sobre o texto Markdown limpo.
- Preservar transparentemente o cabeçalho frontmatter original em metadados para recompô-lo ao salvar o arquivo no disco.
- Adicionar verificação não-bloqueante no deploy para identificar e avisar sobre imagens locais inexistentes em mapas, miniaturas e Markdowns.
- Sinalizar no retorno do deploy se arquivos do `database/` foram modificados, disparando a recarga no editor apenas quando necessário.
- Preservar a seleção e navegação do usuário na árvore de dados durante a recarga.

**Non-Goals:**
- Não remover frontmatters existentes do repositório em massa.
- Não bloquear ou falhar a compilação por conta de imagens inexistentes (apenas emitir `Warning`).
- Não utilizar `QFileSystemWatcher` para recarga automática, evitando condições de corrida e falsos positivos durante operações de salvamento do próprio editor.

## Decisions

### 1. Separação e Preservação de Frontmatter via Metadados
- **Decisão**: Em `CroquiModel.carregar_arquivos_externos`, para arquivos de botão (`secao_textual`), o conteúdo lido será particionado: se contiver `^---\s*\n(.*?)\n---\s*\n(.*)$`, o cabeçalho frontmatter (incluindo delimitadores) é armazenado nos metadados de rascunho (`MetadadosArquivoNoEditor`), enquanto `md.conteudo` recebe estritamente o corpo. No momento de salvar (`extrair_arquivos_e_serializar`), se houver frontmatter preservado nos metadados, ele é re-anexado no início do arquivo.
- **Alternativas consideradas**:
  - *Remover todo frontmatter de arquivos de botões no disco*: Quebraria convenções de licença explícita e exigiria migração na base inteira.
  - *Filtrar apenas na camada de UI (`WidgetEditorMarkdown`)*: Deixaria a propriedade `conteudo` no Protobuf contaminada com frontmatter, propagando a inconsistência.

### 2. Validação Não Bloqueante de Imagens no Deploy
- **Decisão**: Criar a função `verificar_imagens_inexistentes(croqui_dir, croqui_id, compiled_data)` no Passo A do `deploy_generated.py`, inspecionando recursivamente:
  - `caminho_imagem_mapa` em objetos de mapa;
  - `caminho_thumbnail` no croqui;
  - Padrões regex `!\[.*?\]\((.*?)\)` em todos os campos string contendo Markdown (descartando URLs com `http://` ou `https://`).
  Para cada arquivo local não encontrado em `(croqui_dir / caminho_relativo)`, emite um aviso padronizado no terminal:
  `Aviso: A imagem '<caminho>' referenciada no croqui '<croqui_id>' não foi encontrada no disco.`
- **Alternativas consideradas**:
  - *Interromper a compilação com erro*: Inviável no momento, pois existem croquis históricos na base com referências pendentes que ainda não foram corrigidas.

### 3. Sinalização Condicional de Modificação do Database
- **Decisão**: A função `corrigir_database` em `scripts/preparar_submissao_lib.py` passará a rastrear se qualquer alteração em arquivos de `database/` de fato ocorreu e retornará um booleano `modificou_database: bool`.
  - `deploy_generated.deploy` e `workspace.processar_renomeacao_e_compilacao` propagam esse valor para a tarefa de salvamento em background (`TarefaSalvamento`).
  - O sinal `sucesso` do worker emite `(caminho, erros, houve_renomeacao, undo_index, database_modificado)`.
  - Em `_on_salvar_sucesso` no editor, se `database_modificado` for verdadeiro, o editor executa `recarregar_dados_do_disco()`. Caso contrário, mantém o estado atual sem qualquer I/O ou reflow de interface.
- **Alternativas consideradas**:
  - *Recarregar sempre no salvamento*: Desperdiçaria recursos de I/O em 99% dos salvamentos corriqueiros e causaria micro-engasgos na experiência do usuário.

## Risks / Trade-offs

- **[Perda de foco na árvore durante reload condicional]** → Mitigation: Salvar a identificação hierárquica do nó ativo (ex: `caminho_no` ou índice) antes da recarga e restaurá-la imediatamente após a reconstrução do modelo de árvore.
- **[Conflito de estado se o usuário digitar durante o salvamento]** → Mitigation: A recarga só é executada se a pilha de undo estiver limpa (`isClean()` no `undo_index`), garantindo que novas digitações não sejam descartadas.
- **[Markdown contendo separadores '---' no corpo de texto]** → Mitigation: A detecção de frontmatter exige que os três hifens estejam estritamente na primeira linha do arquivo (`lstrip() == "---"`), limitando o split apenas ao primeiro par de delimitadores.
