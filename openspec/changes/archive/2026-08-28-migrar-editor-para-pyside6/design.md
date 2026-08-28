# Design Técnico: Migração do Editor Aresta para PySide6

## Contexto

O projeto `aresta_db` é um ecossistema de código aberto para compilação, validação e manipulação de croquis de escalada, licenciado sob a Mozilla Public License 2.0 (MPL 2.0). A aplicação desktop (Editor Aresta) foi originalmente desenvolvida utilizando `PyQt6`. Como o PyQt6 é regido pela licença GPLv3 (ou comercial proprietária), a distribuição do executável final empacotado impõe copyleft viral em todo o aplicativo, gerando um conflito prático com a intenção do repositório em manter seu código sob MPL 2.0 com integrações permissivas (como Apache 2.0 na API).

A The Qt Company mantém o binding oficial `PySide6` sob a licença LGPLv3. Esta migração substitui a dependência sem alterar a experiência do usuário, mantendo a conformidade com as regras de engenharia descritas em `PRINCIPIOS.md`.

## Metas e Não-Metas

**Metas:**
* Substituir completamente a dependência `pyqt6` por `pyside6` no ambiente de desenvolvimento e em `pyproject.toml`.
* Seguir o ciclo estrito de **TDD (Red-Green-Refactor)** e **Testes de Integração em Primeiro Lugar**, atualizando primeiro os testes de fronteira e unitários e em seguida o código de produção.
* Refatorar todos os módulos em `editor/` (`core`, `models`, `commands`, `controllers`, `views`) e `coleta_de_betas/curadoria/` para importar exclusivamente de `PySide6`.
* Atualizar a declaração de sinais e slots para as convenções canônicas (`pyqtSignal` $\rightarrow$ `Signal`, `pyqtSlot` $\rightarrow$ `Slot`, `pyqtProperty` $\rightarrow$ `Property`).
* Manter a arquitetura de mutação de estado 100% baseada em comandos de histórico (`PySide6.QtGui.QUndoCommand` e `QUndoStack`), respeitando o Princípio VII de `PRINCIPIOS.md`.
* Assegurar **100% de cobertura de testes unitários** e de integração em todos os arquivos `.py` do projeto.
* Garantir que todo código, comentários, docstrings e testes permaneçam estritamente em **português brasileiro** (Princípio I).
* Validar a compilação do executável standalone com `editor/build.py` via PyInstaller.

**Não-Metas:**
* Não criar camadas genéricas ou wrappers de abstração dupla ("suporte híbrido a PyQt6 e PySide6"), respeitando o princípio de **Simplicidade e Anti-Abstração** (Princípio VI). A migração é direta para `PySide6`.
* Não alterar regras de negócio, layouts visuais ou estruturas dos esquemas Protobuf/YAML de croquis.

## Decisões Técnicas

### 1. Adoção do pacote `pyside6` oficial
* **Decisão:** Declarar `"pyside6"` no grupo `[dependency-groups.editor]` em `pyproject.toml`.
* **Alternativas consideradas:** `pyside6-essentials`. Optou-se pelo pacote completo para garantir total suporte a ferramentas estendidas de SVG, fontes e layouts sem dependências ausentes.

### 2. Simplicidade e Migração Direta (Anti-Abstração)
* **Decisão:** Realizar a troca direta e explícita dos imports (`PyQt6` $\rightarrow$ `PySide6`) em cada arquivo, sem introduzir módulos intermediários de compatibilidade (ex: `compat.py`).
* **Rationale:** O Princípio VI de `PRINCIPIOS.md` estabelece *"Melhor um pouco de duplicação do que a abstração errada"* e desaconselha camadas artificiais quando a decisão arquitetural é a transição definitiva para PySide6.

### 3. Preservação do Histórico via `QUndoCommand` (Princípio VII)
* **Decisão:** Utilizar diretamente `PySide6.QtGui.QUndoCommand` e `PySide6.QtGui.QUndoStack` na pilha unificada de histórico do editor (`editor/core/historico.py` e `editor/commands/`).
* **Rationale:** Nenhuma modificação no estado de dados do croqui será feita via callbacks diretos de UI; toda alteração continuará fluindo pela pilha de histórico para permitir desfaça/refaça (Undo/Redo) consistente.

### 4. TDD e Testes de Integração em Primeiro Lugar (Princípios IV e V)
* **Decisão:** A execução das tarefas seguirá o fluxo TDD:
  1. Primeiro, os testes de integração do ciclo de vida da interface e os testes unitários com mocks de Qt (`QStandardPaths`, `QTimer`, `QPixmap`) são adaptados para esperar `PySide6`.
  2. Os testes falham (Red) caso o código ainda importe `PyQt6` ou o ambiente não esteja sincronizado.
  3. O código de produção é migrado para `PySide6` até que todos os testes passem (Green).
  4. O código é refatorado e limpo (Refactor) com checagem de 100% de cobertura.

### 5. Configuração de Mocks e Fixtures de Teste
* **Decisão:** Atualizar os testes que utilizam `@patch("PyQt6...")` para `@patch("PySide6...")` ou para o caminho do módulo importador direto (ex: `@patch("editor.core.storage.QStandardPaths.writableLocation")`).
* **Rationale:** Garante isolamento real e fidelidade nos testes unitários e de integração com `pytest-qt`.

### 6. Idioma e Nomenclatura (Princípio I)
* **Decisão:** Manter todos os nomes de classes, métodos, sinais, slots, variáveis, comentários e testes em português brasileiro (ex: `sinal_campo_alterado = Signal(object, str, object)`).

## Riscos e Mitigações

* **[Risco] Mocks em testes apontando para strings literais antigas:**
  $\rightarrow$ *Mitigação:* Fazer busca exaustiva de padrões de string `PyQt6` em toda a base de testes e atualizar todos os patches.
* **[Risco] Regressão na execução de testes com `pytest-qt`:**
  $\rightarrow$ *Mitigação:* `pytest-qt` detecta PySide6 automaticamente; a execução completa de `pytest` validará cada suite.
* **[Risco] Conflito com empacotamento standalone do PyInstaller:**
  $\rightarrow$ *Mitigação:* O PyInstaller possui suporte nativo de primeira classe a PySide6; o script `editor/build.py` será testado no modo `dist`.

## Plano de Migração

1. **Sincronização de Dependências**: Atualizar `pyproject.toml` para `pyside6` e sincronizar o ambiente virtual.
2. **Adaptação dos Testes (TDD - Red)**: Atualizar arquivos de testes de integração e unitários `*_test.py` no `editor/` e `coleta_de_betas/` com imports e mocks para `PySide6`.
3. **Migração do Código de Produção (TDD - Green)**:
   - `editor/core/` e `editor/models/`
   - `editor/commands/` (preservando `QUndoCommand`)
   - `editor/controllers/` e `editor/views/`
   - `editor/main.py` e `editor/build.py`
   - `coleta_de_betas/curadoria/`
4. **Validação de Cobertura e Refatoração (TDD - Refactor)**: Executar a suíte de testes com medição de cobertura, garantindo 100% de cobertura unitária e de integração.
5. **Teste de Build**: Executar `python editor/build.py test` e validar geração do executável.
