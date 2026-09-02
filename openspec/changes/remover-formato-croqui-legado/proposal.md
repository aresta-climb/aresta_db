## Why

Com a implementação bem-sucedida do Live Reload híbrido (LAN e Cloudflare Relay em `previa.arestaclimb.com`) e o fluxo de submissão direta de Pull Requests via GitHub App, o formato de arquivo proprietário empacotado `.croqui` (ZIP com primeiro byte ofuscado por XOR `0xFF`) tornou-se totalmente obsoleto e redundante. A remoção desta lógica elimina complexidade desnecessária, código frágil de manipulação de binários e rotinas de upload de artefatos para o Cloudflare R2 no CI, consolidando o ecossistema no pareamento em tempo real e na colaboração via Pull Requests.

## What Changes

- **Núcleo do Editor**:
  - **BREAKING**: Remoção completa do módulo `editor/core/croqui_format.py` (`empacotar_croqui`, `ler_croqui`, `ofuscar_primeiro_byte`) e seus testes unitários associados.
  - Remoção dos métodos `exportar_croqui` e `importar_croqui` de `editor/core/croqui_experimental.py`.
  - Remoção da classe `TarefaExportacao` em `editor/core/worker.py`.
- **Interface Gráfica do Editor (Desktop UI)**:
  - Remoção da ação "Exportar .croqui" da barra de ferramentas superior em `editor/legacy_views/area_principal.py`.
  - Remoção do botão "Importar Croqui" da tela inicial em `editor/legacy_views/tela_de_carregamento.py`.
- **CI / CD e Validação de Pull Requests**:
  - Remoção do script `scripts/gerar_croqui_experimental.py` e testes associados.
  - Atualização do utilitário `serving/pr_db_validator.py` para realizar apenas a validação de licenças/cabeçalhos e teste de compilação sem erro via `deploy(...)`, sem gerar ou empacotar arquivos `.croqui`.
  - Limpeza do workflow `.github/workflows/pr-db-validator.yml`, removendo etapas de upload via AWS CLI para Cloudflare R2 e geração de links de download em comentários da PR.
- **Configurações e Metadados do Repositório**:
  - Remoção da associação `*.croqui binary` no `.gitattributes`.
  - Atualização de menções residuais em documentações (`aresta_api/README.md`).

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `croqui-experimental-format`: Remoção dos requisitos e cenários de exportação e importação de arquivos `.croqui`.
- `editor-area-principal`: Remoção do requisito e cenário da ação de exportação de `.croqui` na barra de ferramentas superior.
- `editor-tela-de-carregamento`: Remoção do requisito e cenário do botão de importação de croquis experimentais.
- `ci-cd-workflow-pr`: Remoção da exigência de geração de artefatos `.croqui` e upload para R2 no fluxo de validação de PRs.
- `exportacao-croqui`: Remoção integral dos requisitos do formato proprietário `.croqui`.

## Impact

- **Código Afetado**: `editor/core/croqui_format.py`, `editor/core/croqui_experimental.py`, `editor/core/worker.py`, `editor/legacy_views/area_principal.py`, `editor/legacy_views/tela_de_carregamento.py`, `scripts/gerar_croqui_experimental.py`, `serving/pr_db_validator.py`.
- **Infraestrutura e CI**: Workflow `.github/workflows/pr-db-validator.yml` simplificado sem dependência de credenciais R2/S3.
- **Dependências**: Nenhuma dependência externa adicionada; limpeza de chamadas a `zipfile` associadas ao formato legado.
- **Compatibilidade**: Quebra proposital na capacidade de abrir ou salvar arquivos com extensão `.croqui`. Todos os croquis locais continuarão sendo gerenciados normalmente nas pastas de rascunho de `croquis_experimentais/` ou repositórios locais via Git.
