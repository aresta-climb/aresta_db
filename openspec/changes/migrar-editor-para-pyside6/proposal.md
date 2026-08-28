# Proposal: Migração do Editor Aresta para PySide6

## Why

O repositório `aresta_db` e seus módulos foram relicenciados sob a **Mozilla Public License 2.0 (MPL 2.0)**. No entanto, o Editor Aresta atualmente utiliza **PyQt6**, que é distribuído sob **GPLv3** (copyleft forte/viral) e licença comercial. Ao empacotar e distribuir o executável standalone do Editor Aresta com PyQt6, a GPLv3 sobrepõe-se à distribuição final e impõe copyleft viral em todo o aplicativo distribuído.

A migração para **PySide6** (o binding oficial da The Qt Company sob licença **LGPLv3**) elimina esse conflito de licenciamento, garantindo que o código-fonte do `aresta_db` permaneça 100% MPL 2.0 sem contaminação viral, com conformidade legal plena para publicação em lojas de aplicativos (como Microsoft Store) e integrações abertas.

## What Changes

* **Substituição de Dependência**: Remoção de `pyqt6` e inclusão de `pyside6` no grupo de dependências `editor` do [pyproject.toml](file:///c:/Renato/Devel/aresta-climb/aresta_db/pyproject.toml).
* **Migração de Código do Editor e Views**:
  * Substituição de imports `PyQt6.QtCore`, `PyQt6.QtGui`, `PyQt6.QtWidgets`, `PyQt6.QtTest` para `PySide6.*`.
  * Conversão de primitivas de sinais e slots: `pyqtSignal` $\rightarrow$ `Signal`, `pyqtSlot` $\rightarrow$ `Slot`, `pyqtProperty` $\rightarrow$ `Property`.
* **Adaptação de Módulos de Suporte**: Atualização de módulos auxiliares (como `coleta_de_betas/curadoria`, scripts de build e geração de ícones).
* **Ajuste da Suíte de Testes e Mocks**: Atualização de testes unitários e mocks de paths/objetos Qt (como `QStandardPaths.writableLocation`) para o namespace `PySide6`.
* **Configuração de Build e PyInstaller**: Atualização de [editor/build.py](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/build.py) para garantir empacotamento standalone consistente com PySide6.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capacidade funcional do ponto de vista do usuário final está sendo introduzida -->

### Modified Capabilities
- `editor-arquitetura`: Atualizar o requisito de interface gráfica de desktop para utilizar formalmente PySide6 ao invés de PyQt6.
- `curation-panel`: Atualizar menções de requisitos de interface de curadoria de PyQt para PySide6/Qt.

## Impact

* **Código Afetado**: Todos os arquivos em `editor/`, `coleta_de_betas/curadoria/` e respectivos arquivos de teste `*_test.py` que realizam imports de `PyQt6`.
* **Dependências**: `pyproject.toml` (substituição de `pyqt6` por `pyside6`).
* **Ecossistema de Testes**: `pytest-qt` e `qtawesome` utilizarão automaticamente o backend `PySide6`.
* **Licenciamento**: Conformidade total entre MPL 2.0 (código da aplicação) e LGPLv3 (bindings da biblioteca Qt).
