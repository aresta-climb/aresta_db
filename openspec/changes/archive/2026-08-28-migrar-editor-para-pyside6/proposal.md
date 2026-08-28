# Proposta: Migração do Editor Aresta para PySide6

## Por que

O repositório `aresta_db` e seus módulos foram relicenciados sob a **Mozilla Public License 2.0 (MPL 2.0)**. No entanto, o Editor Aresta atualmente utiliza **PyQt6**, que é distribuído sob **GPLv3** (copyleft forte/viral) e licença comercial. Ao empacotar e distribuir o executável standalone do Editor Aresta com PyQt6, a GPLv3 sobrepõe-se à distribuição final e impõe copyleft viral em todo o aplicativo distribuído.

A migração para **PySide6** (o binding oficial da The Qt Company sob licença **LGPLv3**) elimina esse conflito de licenciamento, garantindo que o código-fonte do `aresta_db` permaneça 100% MPL 2.0 sem contaminação viral, com conformidade legal plena para publicação em lojas de aplicativos (como Microsoft Store) e integrações abertas.

Esta mudança respeita integralmente os princípios inegociáveis do repositório definidos em `PRINCIPIOS.md`: documentação e código 100% em português brasileiro, modularidade *Library-First*, garantia de 100% de cobertura de testes unitários com TDD (Test-Driven Development) estrito, priorização de testes de integração, simplicidade sem camadas desnecessárias de abstração e preservação dos comandos de histórico (`QUndoCommand`).

## O que muda

* **Substituição de Dependência**: Remoção de `pyqt6` e inclusão de `pyside6` no grupo de dependências `editor` do [pyproject.toml](file:///c:/Renato/Devel/aresta-climb/aresta_db/pyproject.toml).
* **Ajuste Conforme TDD nos Testes (Fronteiras e Unidades)**:
  * Atualização dos testes de integração de ciclo de vida do Editor e curadoria para validar o backend PySide6.
  * Atualização dos testes unitários `*_test.py` com novas fixtures, imports de `PySide6` e ajuste dos mocks de APIs do Qt (`QStandardPaths`, `QTimer`, etc.).
* **Migração Direta e Simples do Código de Produção**:
  * Substituição de imports `PyQt6.QtCore`, `PyQt6.QtGui`, `PyQt6.QtWidgets`, `PyQt6.QtTest` para `PySide6.*` em todos os módulos de `editor/` e `coleta_de_betas/`.
  * Conversão de sinais e slots para as primitivas canônicas: `pyqtSignal` $\rightarrow$ `Signal`, `pyqtSlot` $\rightarrow$ `Slot`, `pyqtProperty` $\rightarrow$ `Property`.
  * Preservação integral do padrão de mutação de estado via `PySide6.QtGui.QUndoCommand` na pilha `QUndoStack` do histórico.
* **Scripts de Empacotamento e Build**: Atualização de [editor/build.py](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/build.py) para utilizar PySide6 na geração de ícones e no build standalone via PyInstaller.

## Capacidades

### Novas Capacidades
<!-- Nenhuma nova capacidade funcional do ponto de vista do usuário final está sendo introduzida -->

### Capacidades Modificadas
- `editor-arquitetura`: Atualizar o requisito de interface gráfica desktop para utilizar formalmente PySide6 (LGPLv3) em vez de PyQt6, preservando a inicialização do Qt, loop de aplicação e empacotamento.
- `curation-panel`: Atualizar requisitos da interface gráfica de curadoria para operar com componentes do PySide6.

## Impacto

* **Código Afetado**: Todos os arquivos em `editor/`, `coleta_de_betas/curadoria/` e respectivos arquivos de teste `*_test.py` que utilizam bindings do Qt.
* **Dependências**: `pyproject.toml` (remoção de `pyqt6` e adição de `pyside6`).
* **Ecossistema de Testes**: `pytest-qt` e `qtawesome` vinculados nativamente ao `PySide6`, mantendo 100% de cobertura de testes unitários e de integração.
* **Licenciamento**: Alinhamento jurídico pleno entre MPL 2.0 (código da aplicação) e LGPLv3 (biblioteca Qt).
