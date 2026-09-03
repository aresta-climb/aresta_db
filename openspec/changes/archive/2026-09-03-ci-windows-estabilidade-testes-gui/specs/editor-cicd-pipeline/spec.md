## ADDED Requirements

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