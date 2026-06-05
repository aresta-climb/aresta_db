# Proposal: Notificação Discreta de Salvamento

## Why
Atualmente, o editor exibe uma caixa de diálogo modal (`QMessageBox`) toda vez que o usuário salva o croqui. Isso interrompe o fluxo de trabalho do usuário, exigindo um clique extra para fechar a mensagem. Com a introdução do auto-salvamento (via conexão celular), essa interrupção se torna ainda mais incômoda.

## What Changes
- Substituir o `QMessageBox` de sucesso no salvamento por uma notificação discreta ("Toast").
- A notificação deve aparecer no canto inferior direito da janela principal.
- A notificação deve desaparecer automaticamente após alguns segundos.
- A notificação deve ser visualmente atraente e seguir o estilo do editor.

## Capabilities

### New Capabilities
- `editor-notificacoes`: Sistema de notificações temporárias (Toasts) para feedback não obstrutivo.

### Modified Capabilities
- `editor-area-principal`: Atualizar o cenário de salvamento para usar a nova forma de notificação.

## Impact
- `JanelaPrincipal`: Alteração no método `salvar_croqui`.
- `editor/views/notificacao.py`: Nova biblioteca de UI para o widget de notificação.
- `editor/views/area_principal_test.py`: Atualização dos testes para validar a nova UI.
