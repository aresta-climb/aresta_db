## Context

O tempo atual para execução de testes unitários e de integração locais é de aproximadamente 34 segundos. Como o projeto tem crescido, isso cria um gargalo no fluxo de feedback rápido para o desenvolvedor. Além disso, testes paralelos ou isolados falham com falha de segmentação ao tentar usar o PyQt6 sem um loop de aplicação (`QApplication`) devidamente instanciado no processo correspondente.

## Goals / Non-Goals

**Goals:**
- Reduzir o tempo de feedback de testes locais de 34s para menos de 1s para execuções onde nenhum código relevante foi modificado.
- Permitir execução paralela em múltiplos processos locais para acelerar testes completos.
- Garantir estabilidade da suite de testes de integração e visualização em PyQt6 quando rodando em paralelo no Windows.

**Non-Goals:**
- Não alterar o comportamento funcional de nenhuma feature ou regra de negócio do banco de dados/editor.
- Não implementar testes em nuvem (CI/CD) nesse escopo; focar no fluxo local (`build.py`).

## Decisions

### Decisão 1: Utilização de pytest-testmon para análise de impacto
- **Alternativa Considerada:** `pytest-picked` (rodar testes baseados em arquivos alterados detectados pelo Git).
- **Raciocínio:** O `pytest-picked` é leve, mas impreciso (roda todos os testes no arquivo alterado e não detecta se alterações em arquivos de implementação impactam testes em outros arquivos). O `pytest-testmon` mapeia dependências exatas no nível de linha por meio de rastreamento de cobertura, oferecendo maior precisão e rapidez.

### Decisão 2: Utilização de pytest-xdist para paralelização local
- **Alternativa Considerada:** Execução paralela via subprocessos ad-hoc ou `pytest-parallel`.
- **Raciocínio:** O `pytest-xdist` é o padrão da indústria, estável e ativamente mantido, além de ser perfeitamente compatível com o `pytest-testmon` desde a versão 1.4.0.

### Decisão 3: Injeção da fixture `qapp` no teste de QR Code do servidor celular
- **Alternativa Considerada:** Usar a flag de ambiente `QT_QPA_PLATFORM=offscreen`.
- **Raciocínio:** A flag `offscreen` apenas oculta a janela física, mas não inicializa a `QApplication` exigida por classes como `QPixmap` no PyQt6 em um novo processo isolado do `pytest-xdist`. Declarar explicitamente a dependência de `qapp` (ou `qtbot`) na assinatura do teste garante a inicialização correta em qualquer worker thread do `pytest-xdist`.

## Risks / Trade-offs

- **Instabilidade em Paralelo (Race Conditions)**: Testes que alteram estados globais ou escrevem no mesmo caminho de arquivo físico podem falhar ao rodar concorrentemente.
  - *Mitigação*: A maioria dos testes neste repositório já usa caminhos temporários (`tmp_path`) de forma limpa. Se houver falhas específicas de concorrência, o desenvolvedor poderá desativar a paralelização no `build.py`.
- **Cache do Testmon Desatualizado**: Alterações complexas de infraestrutura de teste ou imports dinâmicos podem fazer o `pytest-testmon` ignorar alterações relevantes.
  - *Mitigação*: Adicionar suporte a um comando ou flag `--force` no `build.py` que limpa o cache do testmon e força a re-execução total.
