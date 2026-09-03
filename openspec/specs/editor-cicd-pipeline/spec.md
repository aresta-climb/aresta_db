## Purpose

Define os requisitos para automação de empacotamento, compilação e lançamento do executável do Editor Aresta no pipeline de CI/CD.
## Requirements
### Requirement: Editor release automation
O sistema DEVE (SHALL) compilar e publicar o executável do editor mediante acionamento manual em um ambiente de dependências isolado, etiquetando a versão com a numeração semântica fornecida e garantindo que o tamanho do binário permaneça estritamente dentro dos limites de otimização (< 95MB).

#### Scenario: User triggers the workflow
- **WHEN** um mantenedor do repositório disparar o fluxo de trabalho de lançamento informando uma versão semântica válida
- **THEN** o sistema compila o executável para Windows utilizando o ambiente isolado do grupo `editor`, cria uma Release no GitHub anexada à nova tag do git, e faz o upload do arquivo `.exe` otimizado

### Requirement: Dev cycle progression
The system SHALL automatically bump the repository back to a development state after a successful release.

#### Scenario: Post-release bumping
- **WHEN** the release artifact has been uploaded and tagged successfully
- **THEN** the system calculates the next minor version, appends `-dev`, modifies the version file, and commits this back to the main branch

### Requirement: Completude da Suíte de Testes no Sparse Checkout do CI
O workflow de CI/CD DEVE (SHALL) incluir o diretório de testes arquiteturais e estáticos `tests/` no sparse-checkout dos jobs de teste de PR e de release.

#### Scenario: Execução da etapa de testes com sparse checkout
- **WHEN** o job de validação de PR ou de release é disparado com checkout otimizado (sparse-checkout)
- **THEN** o sistema baixa os diretórios de código e o diretório `tests/`
- **AND** executa 100% dos testes do repositório (incluindo tipagem estática e checagem AST)

### Requirement: Supressão do Windows Error Reporting no Runner de Lançamento
O workflow de lançamento no Windows DEVE (SHALL) suprimir a interface gráfica e o bloqueio de relatórios de falha do Windows (WerFault.exe) antes da execução da suíte de testes.

#### Scenario: Encerramento imediato em falha nativa não tratada
- **WHEN** um processo de teste sofre uma falha fatal nativa ou Access Violation em ambiente Windows não-interativo
- **THEN** o kernel do Windows encerra o processo imediatamente sem exibir diálogos bloqueantes
- **AND** o pytest-xdist detecta o término do worker e o substitui automaticamente sem travar a execução


