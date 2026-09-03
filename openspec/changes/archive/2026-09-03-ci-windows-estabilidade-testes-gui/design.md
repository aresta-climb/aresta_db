## Context

Nos workflows de CI/CD do GitHub Actions, a execução de testes automatizados com `pytest -n auto` travava no runner do Windows (`release-editor.yml`) a exatamente 97%, após concluir 1.224 testes. O processo permanecia bloqueado até que o timeout da etapa de 10 minutos forçasse o encerramento do job. Além disso, os testes da pasta `tests/` (11 testes focados em tipagem estática e conformidade arquitetural com `mypy --strict`) eram omitidos tanto no validador de PR (`pr-code-validator.yml`) quanto no release, por não constarem no bloco de `sparse-checkout`.

A investigação identificou que o PySide6/Qt sob driver `offscreen` no Windows acumulava eventos tardios de deleção (`deleteLater()`) gerados na inicialização de `JanelaPrincipal`. Ao executar dezenas de testes de interface gráfica em um único worker de longa duração (já que o Windows runner do GitHub Actions possui apenas 2 vCPUs), ocorria um Access Violation nativo em C++ durante o teardown do `pytestqt` (`_process_events`). No Windows não-interativo do GitHub Actions, o `WerFault.exe` interceptava a falha e congelava o processo worker indefinidamente, mantendo os canais IPC abertos e impedindo o `pytest-xdist` de detectar a morte do worker e substituí-lo.

Este documento de design estabelece como as soluções serão implementadas em estrita observância aos mandamentos de `PRINCIPIOS.md`: Tudo em Português, TDD (Red-Green-Refactor), 100% de cobertura de testes unitários, testes de integração em primeiro lugar e simplicidade declarativa anti-abstração.

## Goals / Non-Goals

**Goals:**
- Garantir que o workflow de release do editor no Windows conclua 100% dos testes (1.263 itens) sem travar.
- Impedir que qualquer falha nativa em subprocessos congele os runners do Windows através da supressão do `WerFault.exe`.
- Incluir o diretório `tests/` no `sparse-checkout` em todos os workflows de CI que executam `pytest` (`pr-code-validator.yml` e `release-editor.yml`).
- Eliminar o antipadrão de alocação de widgets descartados com `deleteLater()` na inicialização das páginas concretas da `JanelaPrincipal`.
- Padronizar uma fixture com teardown (`yield` seguido de `janela.close()`) para os testes de `JanelaPrincipal` em `area_principal_test.py`.
- Eliminar duplicatas de testes em `editor/legacy_views/area_principal_test.py`.
- Observar integralmente o ciclo TDD (Red-Green-Refactor) com 100% de cobertura e testes de integração prévios.

**Non-Goals:**
- Modificar o comportamento funcional do Editor Aresta para o usuário final.
- Alterar as regras de validação de PRs do banco de dados (`database/`).
- Mudar a biblioteca gráfica ou a versão do PySide6.

## Decisions

### 1. Desativação do WerFault no Windows Runner via Registro (Princípio VI: Simplicidade e Resiliência)
- **Decisão**: Adicionar um passo prévio no workflow do Windows executando PowerShell:
  ```powershell
  New-Item -Path "HKLM:\SOFTWARE\Microsoft\Windows\Windows Error Reporting" -Force | Out-Null
  Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\Windows Error Reporting" -Name "DontShowUI" -Value 1
  Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\Windows Error Reporting" -Name "Disabled" -Value 1
  ```
- **Racional**: Em sessões headless sem desktop interativo, qualquer diálogo modal do Windows trava o processo indefinidamente. Desativando a interface do relatório de erros, qualquer processo com falha fatal encerra imediatamente, permitindo que o `pytest-xdist` detecte o término do worker via EOF no pipe e acione o mecanismo nativo de substituição de nó (`replacing crashed worker`).
- **Alternativas consideradas**: Ajustar timeouts individuais por teste com `pytest-timeout`. Rejeitado como solução primária porque não evita o processo zumbi travando a fila do xdist no nível do sistema operacional.

### 2. Inclusão de `tests/` no Sparse Checkout dos Workflows (Princípio III: 100% de Cobertura)
- **Decisão**: Adicionar a linha `tests` na especificação de `sparse-checkout` de `pr-code-validator.yml` e `release-editor.yml`.
- **Racional**: Assegura paridade exata entre as suítes locais e remotas (1.263 testes). Os testes em `tests/` validam `mypy --strict` e conformidade de anotações AST em 100% dos arquivos Python de produção.

### 3. Refatoração de `PaginaBase` e Inicialização das Páginas (Princípio VI: Simplicidade e Anti-Abstração)
- **Decisão**: Em `editor/legacy_views/area_principal.py`, tornar a criação do label placeholder condicional em `PaginaBase` (ou seja, só criar o `QLabel` se a subclasse for uma página placeholder pura como `PaginaHistorico`, sem layout próprio). Nas páginas especializadas (`PaginaDados`, `PaginaImagens`, `PaginaMapas`, `PaginaBetas`), remover a chamada a `removeWidget` e `self.label.deleteLater()`.
- **Racional**: Elimina o desperdício de instanciar e agendar a deleção tardia de 4 widgets C++ por janela, estabilizando a heap do Qt sob o driver `offscreen`.
- **Abordagem TDD**: Antes de alterar o código de produção, escrever teste unitário específico que verifica que a instanciação das páginas não deixa widgets pendentes de destruição assíncrona.

### 4. Fixture do Pytest com Teardown Explícito para `JanelaPrincipal` (Princípio IV e V: TDD e Integração)
- **Decisão**: Criar a fixture `janela_principal` em `area_principal_test.py`:
  ```python
  @pytest.fixture
  def janela_principal(qtbot):
      janela = JanelaPrincipal()
      qtbot.addWidget(janela)
      yield janela
      janela.close()
  ```
  Para testes que demandam customizações na construção (`auth`, `workspace`), criar um gerenciador de contexto declarativo simples ou fixture parametrizada:
  ```python
  @contextmanager
  def criar_janela_teste(qtbot, **kwargs):
      janela = JanelaPrincipal(**kwargs)
      qtbot.addWidget(janela)
      try:
          yield janela
      finally:
          janela.close()
  ```
- **Racional**: Garante que o fechamento da janela (`closeEvent`) e a liberação de conexões de sinais ocorram deterministicamente antes que o teardown do `pytestqt` processe eventos residuais no loop de eventos.

### 5. Remoção de Código Duplicado em `area_principal_test.py` (Princípio I e VI)
- **Decisão**: Excluir o bloco repetido entre as linhas 455 e 640 que redefinia testes já presentes nas linhas 239 a 454.
- **Racional**: Elimina redundância, reduz tempo de execução e simplifica a manutenção da suíte de testes.

## Observância aos Princípios de Engenharia (PRINCIPIOS.md)

1. **Tudo em Português**: Todo o código, fixture, documentação, especificações, nomes de variáveis e comentários são integralmente em português brasileiro.
2. **Library-First**: As rotinas de ciclo de vida e teardown operam de forma isolada, permitindo que cada componente seja testado de maneira autônoma.
3. **100% de Cobertura de Testes Unitários**: A inclusão de `tests/` e a manutenção rigorosa de testes para todas as ramificações de `PaginaBase` e `JanelaPrincipal` garantem cobertura completa.
4. **Imperativo do TDD (Red-Green-Refactor)**: Os testes que verificam o ciclo de vida limpo das páginas são criados e executados primeiro (Red), seguidos da implementação (Green) e subsequente padronização e limpeza (Refactor).
5. **Testes de Integração em Primeiro Lugar**: A verificação final executa a suíte de integração de ponta a ponta simulando as condições exatas do CI (2 workers no Windows).
6. **Simplicidade e Anti-Abstração**: A fixture com `yield` e o gerenciador de contexto direto evitam o excesso de engenharia ou classes fábricas desnecessárias.

## Risks / Trade-offs

- **[Risco] Testes que modificam workspace ou parâmetros específicos de `JanelaPrincipal`** → *Mitigação*: Uso do gerenciador de contexto `criar_janela_teste` que aceita `**kwargs` mantendo o teardown seguro garantido no bloco `finally`.
- **[Risco] Falhas nativas residuais em outros componentes de interface** → *Mitigação*: A supressão de diálogos do WerFault no runner garante que qualquer crash encerre o processo imediatamente sem travar o CI por 10 minutos.

## Migration Plan

1. Configurar supressão de diálogos do WerFault no workflow `release-editor.yml`.
2. Adicionar `tests` ao sparse-checkout em `release-editor.yml` e `pr-code-validator.yml`.
3. Escrever teste unitário (TDD Red) para o ciclo de vida sem `deleteLater()` das páginas.
4. Refatorar a inicialização de `PaginaBase` e subclasses em `area_principal.py` (TDD Green).
5. Implementar fixture de teardown e limpar testes duplicados em `area_principal_test.py` (TDD Refactor).
6. Validar localmente com 2 workers simulando o CI garantindo 1.263 testes aprovados sem avisos ou crashes.