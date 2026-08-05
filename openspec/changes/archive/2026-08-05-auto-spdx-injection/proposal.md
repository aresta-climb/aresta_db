## Why

Para garantir que as licenças e copyrights estejam presentes em todos os croquis, sem depender da memória dos contribuidores ou do editor. Como a biblioteca `PyYAML` remove comentários ao ler e reescrever arquivos YAML e Markdown (frontmatter), a automação de deploy deve atuar como um mecanismo para restaurar/preservar as duas linhas cruciais de comentários de licenciamento. Isso garante conformidade legal contínua sem esforço manual e evita que o build apague os comentários.

## What Changes

- A função `corrigir_database` no `scripts/preparar_submissao_lib.py` (ou `salvar_md_com_frontmatter`/`processar_croqui_yaml`) será atualizada para garantir que as seguintes linhas de comentários estejam sempre presentes:
  ```yaml
  # SPDX-License-Identifier: ODbL-1.0
  # Copyright (C) 2026 Aresta Contributors
  ```
- **Injeção via Comentário**: A injeção não será feita como um campo do dicionário YAML (o que violaria o schema do Protobuf), mas sim estritamente como linhas de comentários inseridas diretamente no arquivo físico.
- Adição de testes em TDD cobrindo cenários para garantir a presença dos comentários nos arquivos processados.

## Capabilities

### New Capabilities
- `auto-spdx-injection`: Preservação e injeção automática das duas linhas de comentário (SPDX e Copyright) nos arquivos de banco de dados (`.yaml` e `.md`).

### Modified Capabilities
- Nenhuma.

## Impact

- **Código**: `scripts/preparar_submissao_lib.py` (nova lógica de injeção de string antes do dump do YAML).
- **Testes**: Criação/Atualização em `tests/test_spdx_comments.py`.
- **Pipeline (CI)**: Quando o script for rodado no CI ou no fluxo do usuário, os arquivos no disco receberão (ou manterão) as linhas de comentário no topo.
