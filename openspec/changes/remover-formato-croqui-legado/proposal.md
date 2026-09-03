## Why

Com a implementação e consolidação do recarregamento em tempo real (Live Reload híbrido via rede local e retransmissor na nuvem em `previa.arestaclimb.com`) e o fluxo de publicação oficial direta de Pull Requests via GitHub App, o formato de arquivo proprietário empacotado `.croqui` (arquivo compactado com primeiro byte ofuscado por XOR `0xFF`) tornou-se obsoleto, redundante e desnecessário.

A remoção completa desta lógica elimina complexidade acidental, manipulações frágeis de arquivos compactados e rotinas de envio de artefatos para armazenamento em nuvem (Cloudflare R2) no fluxo de integração contínua (CI), simplificando a arquitetura em estrita observância aos princípios de engenharia definidos em `PRINCIPIOS.md`.

## What Changes

- **Núcleo do Editor (`editor/core/`)**:
  - **QUEBRA DE COMPATIBILIDADE (BREAKING)**: Remoção integral do módulo de biblioteca `editor/core/croqui_format.py` (`empacotar_croqui`, `ler_croqui`, `ofuscar_primeiro_byte`) e de seu respectivo arquivo de testes unitários `editor/core/croqui_format_test.py`.
  - Remoção dos métodos `exportar_croqui` e `importar_croqui` da biblioteca `editor/core/croqui_experimental.py`, preservando as rotinas locais de ciclo de vida de rascunhos.
  - Remoção da classe assíncrona de exportação `TarefaExportacao` em `editor/core/worker.py`.
- **Interface Gráfica do Editor Desktop (`editor/legacy_views/`)**:
  - Remoção da ação "Exportar .croqui" da barra superior em `editor/legacy_views/area_principal.py`.
  - Remoção do botão "Importar Croqui" da tela inicial em `editor/legacy_views/tela_de_carregamento.py`.
- **Integração Contínua e Validação de Contribuições (`serving/` e CI)**:
  - Exclusão do script utilitário `scripts/gerar_croqui_experimental.py` e de seus testes de integração associados.
  - Refatoração da biblioteca `serving/pr_db_validator.py` para validar conformidade de licenças/cabeçalhos e testar a compilação diretamente via rotina canônica `deploy(...)`, sem gerar ou empacotar arquivos `.croqui`.
  - Simplificação do fluxo de CI `.github/workflows/pr-db-validator.yml`, removendo etapas de upload via AWS CLI para o Cloudflare R2 e remoção de links de download em comentários do Pull Request.
- **Configurações e Metadados do Repositório**:
  - Remoção da associação `*.croqui binary` no arquivo `.gitattributes`.
  - Limpeza de menções residuais em documentações (`aresta_api/README.md`).
- **Conformidade Estrita com `PRINCIPIOS.md`**:
  - **I. Tudo em Português**: Nomenclatura, documentação e mensagens integralmente em português brasileiro.
  - **II. Biblioteca em Primeiro Lugar (Library-First)**: Rotinas isoladas, coesas e autossuficientes.
  - **III. 100% de Cobertura de Testes Unitários**: Cobertura mantida em 100% em todos os módulos alterados.
  - **IV. Imperativo do Teste em Primeiro Lugar (TDD)**: Ciclo Vermelho-Verde-Refatorar em todas as fases.
  - **V. Testes de Integração em Primeiro Lugar**: Validação prévia de contratos intermódulos antes de alterações pontuais.
  - **VI. Simplicidade e Anti-Abstração**: Eliminação de código morto sem camadas artificiais de compatibilidade.
  - **VII. Edições de Estado via Histórico**: Preservação da integridade da pilha de comandos do editor.

## Capabilities

### New Capabilities
Nenhuma.

### Modified Capabilities
- `croqui-experimental-format`: Remoção dos requisitos e cenários de exportação e importação de arquivos `.croqui`.
- `editor-area-principal`: Remoção do requisito e cenário da ação de exportação de `.croqui` na barra de ferramentas superior.
- `editor-tela-de-carregamento`: Remoção do requisito e cenário do botão de importação de croquis experimentais.
- `ci-cd-workflow-pr`: Remoção da exigência de geração de artefatos `.croqui` e upload para R2 no fluxo de validação de Pull Requests.
- `exportacao-croqui`: Remoção integral dos requisitos do formato proprietário `.croqui`.

## Impact

- **Código Afetado**: `editor/core/croqui_format.py`, `editor/core/croqui_experimental.py`, `editor/core/worker.py`, `editor/legacy_views/area_principal.py`, `editor/legacy_views/tela_de_carregamento.py`, `scripts/gerar_croqui_experimental.py`, `serving/pr_db_validator.py`.
- **Infraestrutura e CI**: Workflow `.github/workflows/pr-db-validator.yml` simplificado, mais rápido e sem dependência de credenciais R2/S3.
- **Compatibilidade**: Quebra proposital na capacidade de abrir ou salvar arquivos com extensão `.croqui`. Todos os croquis locais continuarão sendo gerenciados normalmente nas pastas de rascunho de `croquis_experimentais/` ou repositórios locais via Git.
