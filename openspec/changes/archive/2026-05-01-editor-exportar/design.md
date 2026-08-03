## Context

O Editor Aresta permite que usuários criem croquis experimentais locais. Para facilitar o compartilhamento desses croquis, é necessário um formato de arquivo portátil. O formato escolhido é o `.croqui`, que é um ZIP ofuscado. Atualmente, a funcionalidade de exportação está quebrada e a de importação incompleta.

## Goals / Non-Goals

**Goals:**
- Implementar exportação funcional com ofuscação de magic number.
- Implementar importação robusta que suporte o formato ofuscado.
- Garantir que a lógica de manipulação do formato seja independente da UI (Library-First).
- Fornecer feedback visual durante operações de arquivo.

**Non-Goals:**
- Implementar criptografia forte (a ofuscação é apenas para evitar abertura acidental por outros apps).
- Suportar exportação de múltiplos croquis simultaneamente.

## Decisions

- **Biblioteca `croqui_format.py`**: Criar uma nova biblioteca no `editor/core/` para encapsular toda a lógica de ZIP e ofuscação. Isso facilita o teste e a reutilização.
- **Ofuscação via XOR 0xFF**: O primeiro byte do arquivo ZIP (`P` ou `0x50`) será transformado em `0xAF`. Isso é suficiente para que sistemas operacionais e utilitários de ZIP não reconheçam o arquivo automaticamente.
- **Uso de Workers**: A exportação e importação serão realizadas através da infraestrutura de `TarefaWorker` já existente para evitar congelamento da interface.
- **Normalização na Importação**: Ao importar, o sistema deve garantir que não haja pastas aninhadas desnecessárias (ex: se o ZIP contiver `pasta/arquivo`, e não apenas os arquivos na raiz).

## Risks / Trade-offs

- **[Risco] Corrupção de arquivo** → [Mitigação] O processo de ofuscação só ocorre após o fechamento seguro do arquivo ZIP. A importação fará a desofuscação em memória ou via `r+b` para evitar perda de dados.
- **[Risco] Performance em arquivos grandes** → [Mitigação] Uso de worker threads com feedback de progresso.
- **[Trade-off] Ofuscação vs Transparência** → Escolhemos ofuscar para reforçar a identidade do formato `.croqui`, mesmo que isso exija uma etapa extra de processamento.
