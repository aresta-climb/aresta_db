# Design: Migração do Editor Aresta para PySide6

## Context

O projeto `aresta_db` é um ecossistema open-source para gestão e compilação de croquis de escalada, licenciado sob a Mozilla Public License 2.0 (MPL 2.0). O subcomponente de desktop (Editor Aresta) foi originalmente escrito usando `PyQt6`. Como o PyQt6 é regido pela licença GPLv3 (ou comercial paga), qualquer distribuição de executável compilado força a aplicação inteira sob a GPLv3, gerando uma incompatibilidade prática com a intenção do projeto em manter o código sob MPL 2.0 com integrações permissivas (como Apache 2.0 na API).

A The Qt Company mantém o binding oficial `PySide6` sob a licença LGPLv3. A migração técnica substitui o binding sem alterar a arquitetura funcional do Editor.

## Goals / Non-Goals

**Goals:**
* Substituir completamente a dependência `pyqt6` por `pyside6` no ambiente e no `pyproject.toml`.
* Refatorar todos os módulos do Editor, Views, Controllers, Models, Workers e Ferramentas de Suporte para importar de `PySide6`.
* Atualizar a declaração de sinais e slots (`pyqtSignal` $\rightarrow$ `Signal`, `pyqtSlot` $\rightarrow$ `Slot`, `pyqtProperty` $\rightarrow$ `Property`).
* Atualizar toda a suíte de testes automatizados (`pytest-qt` e mocks de paths/APIs do Qt) para garantir 100% de passagem nos testes.
* Validar o script de build standalone `editor/build.py` via PyInstaller com PySide6.

**Non-Goals:**
* Não redesenhar a arquitetura visual nem componentes da UI (o comportamento visual e a experiência do usuário devem permanecer idênticos).
* Não alterar regras de negócio ou estrutura dos dados protobuf e yaml de croquis.

## Decisions

### 1. Adoção do pacote `pyside6` completo
* **Decisão:** Declarar `"pyside6"` nas dependências do grupo `editor` em `pyproject.toml`.
* **Alternativas:** `pyside6-essentials` (pacote menor sem add-ons). Optou-se por `pyside6` completo para garantir total compatibilidade com utilitários de SVG, animações e ferramentas estendidas caso necessário.

### 2. Conversão de Sintaxe de Sinais e Slots
* **Decisão:** Substituir `pyqtSignal` por `PySide6.QtCore.Signal` e `pyqtSlot` por `PySide6.QtCore.Slot`.
* **Rationale:** É a convenção canônica do PySide e do Qt for Python.

### 3. Tratamento de Mocks em Testes
* **Decisão:** Mocks que realizam `@patch("PyQt6.QtCore.QStandardPaths.writableLocation")` serão atualizados para `@patch("PySide6.QtCore.QStandardPaths.writableLocation")` ou pelo caminho relativo ao módulo sob teste (`@patch("editor.core.storage.QStandardPaths.writableLocation")`).
* **Rationale:** Evita falhas de importação de módulos inexistentes durante a execução da suíte de testes.

### 4. Integração com `pytest-qt` e `qtawesome`
* **Decisão:** Manter `pytest-qt` e `qtawesome` inalterados no `pyproject.toml`.
* **Rationale:** O `pytest-qt` detecta e se vincula automaticamente ao PySide6 quando presente no ambiente virtual. O `qtawesome` utiliza a biblioteca `QtPy` como abstração interna, que seleciona PySide6 nativamente.

### 5. Build PyInstaller
* **Decisão:** Manter os argumentos do PyInstaller em `editor/build.py`, atualizando os imports de apoio de `PyQt6` para `PySide6` e conferindo a coleta de metadados. O PyInstaller possui suporte nativo a PySide6 através de seus hooks padrões.

## Risks / Trade-offs

* **[Risco] Mocks em testes apontando para strings de namespace antigo:**
  $\rightarrow$ *Mitigação:* Realizar busca global de strings (`grep`) por `PyQt6` em todo o diretório de testes e atualizar todos os patches.
* **[Risco] Diferenças sutis de destruição de objetos em C++ (Shiboken vs SIP):**
  $\rightarrow$ *Mitigação:* A arquitetura do Editor já utiliza gerenciamento de pais (`parent`) e MVC estrito; rodar a suíte completa de testes com `pytest -v` e testar a inicialização da UI.
* **[Risco] Sobra de resquícios de arquivos `.pyc` ou ambiente virtual com PyQt6 instalado:**
  $\rightarrow$ *Mitigação:* Recomendar sincronização do ambiente com `uv sync` para remover pacotes órfãos.

## Migration Plan

1. Atualizar `pyproject.toml` substituindo `pyqt6` por `pyside6`.
2. Executar refatoração nos módulos de código-fonte (`editor/`, `coleta_de_betas/curadoria/`).
3. Atualizar scripts de build e geração de recursos (`editor/build.py`).
4. Atualizar arquivos de testes unitários e de integração (`*_test.py`).
5. Rodar a suíte completa de testes com `pytest`.
