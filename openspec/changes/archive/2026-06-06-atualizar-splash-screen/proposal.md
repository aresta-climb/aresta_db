## Why

A tela de abertura atual utiliza um ícone genérico e não permite movimentação pelo usuário, o que causa estranheza e prejudica a usabilidade, especialmente quando o sistema aguarda interações externas como a autenticação do GitHub. Precisamos alinhar a identidade visual do Editor com o aplicativo principal (aresta_app) e melhorar a experiência do usuário permitindo que a tela seja movida livremente.

## What Changes

- Cópia das logos novas do repositório `aresta_app/frontend/assets` para o repositório local do `aresta_db` (ex: `editor/recursos/`).
- O ícone da Tela de Abertura passará a ser a arte oficial do Aresta Climb (e.g. `logo_splash.png` ou `logo_app.png`).
- Implementação de funcionalidade drag-and-drop (arrastar) para a `TelaDeAbertura` (janela frameless), reimplementando os eventos de mouse (`mousePressEvent`, `mouseMoveEvent`).
- O desenvolvimento será guiado por testes (TDD), exigindo a escrita de testes unitários para o arrasto de janelas usando `QTest` antes da implementação das lógicas.

## Capabilities

### New Capabilities

- `splash-screen-draggable`: Permitir que janelas sem borda (FramelessWindowHint) sejam movidas pelo usuário através do clique e arraste no fundo.

### Modified Capabilities


## Impact

- Código modificado: `editor/views/tela_de_abertura.py`, `editor/main.py`.
- Adição ou uso de novos assets visuais de forma oficial no projeto (arte do aresta_app).
- O processo de build / bundle (`ArestaEditor.spec` e/ou `build.py`) precisará ser modificado para incluir a nova pasta de recursos na geração do executável.
