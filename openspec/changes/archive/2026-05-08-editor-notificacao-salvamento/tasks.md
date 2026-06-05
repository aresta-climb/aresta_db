## 1. Componentes de UI e Estilo

- [x] 1.1 Criar testes para o widget de notificação em `editor/views/notificacao_test.py`.
- [x] 1.2 Implementar o widget `NotificacaoToast` em `editor/views/notificacao.py`.
- [x] 1.3 Adicionar lógica de animação de fade-out e auto-destruição no widget.

## 2. Integração na Janela Principal

- [x] 2.1 Implementar método `exibir_notificacao` na classe `JanelaPrincipal`.
- [x] 2.2 Substituir chamadas de `QMessageBox.information` por `self.exibir_notificacao` no método `salvar_croqui`.
- [x] 2.3 Atualizar os testes em `editor/views/area_principal_test.py` para validar a nova interação de salvamento.

## 3. Verificação Final

- [x] 3.1 Executar bateria completa de testes automatizados.
- [x] 3.2 Verificar visualmente o posicionamento e animação da notificação.
- [x] 3.3 Arquivar a mudança usando `/opsx-archive`.
