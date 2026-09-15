## Why

Ao salvar um croqui no Editor Aresta em modo local (diretamente dentro do repositório de desenvolvimento no Windows), o processo falhava com erros repetidos do tipo `[Errno 22] Invalid argument` ao tentar injetar os cabeçalhos SPDX e Copyright nos arquivos Markdown (`.md`) durante o pipeline de compilação pós-salvamento.
Isso ocorria devido a um ciclo de *double-write*: o editor salvava os arquivos `.md` usando `yaml.dump` (que descarta comentários, removendo o SPDX previamente existente), e milissegundos depois, na compilação, `garantir_comentarios_licenca` tentava reescrever os mesmos 15 arquivos para reinjetar o SPDX. Como o primeiro lote de gravações disparava imediatamente o File Watcher do Git / VS Code, os arquivos estavam temporariamente abertos via `mmap` (`CreateFileMapping`), fazendo com que a chamada subsequente `open(file_path, "w")` (truncate) falhasse no Windows com o erro de kernel `ERROR_USER_MAPPED_FILE` (1224), mapeado para `[Errno 22] Invalid argument`.

## What Changes

- **Injeção Nativa de SPDX no Salvamento do Editor**: As rotinas de serialização de arquivos Markdown e YAML no editor (`_salvar_objeto_com_frontmatter` em `croqui_model.py`, `salvar_md_com_frontmatter` em `preparar_submissao_lib.py` e a gravação de `croqui.yaml` em `worker.py`) passam a emitir o frontmatter e cabeçalho já contendo obrigatoriamente as linhas de comentário SPDX e Copyright.
- **Eliminação do Double-Write**: Como os arquivos já são persistidos no disco com o cabeçalho SPDX intacto desde o primeiro salvamento, a etapa `garantir_comentarios_licenca` da compilação identifica a presença válida do cabeçalho e encerra sem efetuar reescritas redundantes em disco.
- **Resiliência contra Travamentos Transitórios no Windows**: A função `garantir_comentarios_licenca` passa a capturar exceções `OSError` (como `[Errno 22]` e `[Errno 13]`) e aplicar uma política de retentativa curta com backoff linear/exponencial (ex.: até 3 tentativas com pausa de 50-100ms) para tolerar inspeções transitórias de ferramentas do sistema (Git, VS Code, indexadores ou antivírus).

## Capabilities

### Modified Capabilities
- `auto-spdx-injection`: Requisitos atualizados para exigir que serializadores de Markdown e YAML em disco já gerem os comentários de licença nativamente no primeiro write, e que o injetor possua política de tolerância/retentativa a bloqueios transitórios de I/O em ambiente Windows.

## Impact

- `editor/models/croqui_model.py`: Inclusão dos comentários SPDX/Copyright no frontmatter gerado em `_salvar_objeto_com_frontmatter`.
- `scripts/preparar_submissao_lib.py`: Inclusão dos comentários SPDX/Copyright em `salvar_md_com_frontmatter` e tratamento com retentativa em `garantir_comentarios_licenca`.
- `editor/core/worker.py`: Garantia de comentários SPDX/Copyright no dump de `croqui.yaml` em `TarefaSalvamento`.
- Testes unitários correspondentes em `editor/models/croqui_model_test.py`, `scripts/preparar_submissao_lib_test.py` e `editor/core/worker_test.py`.
