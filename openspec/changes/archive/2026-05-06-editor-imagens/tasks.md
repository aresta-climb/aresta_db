## 1. Testes de Integração e Contratos (Red Phase)

- [x] 1.1 Criar teste de integração em `editor/views/area_principal_imagens_integracao_test.py` que valide que a `PaginaImagens` contém o `WidgetEditorImagens` e responde ao salvamento global.
- [x] 1.2 Criar `editor/views/widget_editor_imagens_test.py` definindo os testes para o contrato do novo widget (inicialização com `modo_integrado`, listagem de imagens e método `salvar_alteracoes`).
- [x] 1.3 Executar os testes e confirmar que todos FALHAM conforme esperado.

## 2. Refatoração e Implementação (Green Phase)

- [x] 2.1 Criar `editor/views/widget_editor_imagens.py` extraindo as classes e a lógica do script original para satisfazer os testes unitários.
- [x] 2.2 Implementar a lógica de ocultar o botão de salvamento quando `modo_integrado=True`.
- [x] 2.3 Implementar o método `salvar_alteracoes()` no widget.
- [x] 2.4 Executar os testes unitários e garantir que todos PASSAM (Green).

## 3. Integração e Refatoração (Refactor Phase)

- [x] 3.1 Atualizar `editor/views/janela_principal.py` para integrar o `WidgetEditorImagens` e fazer os testes de integração passarem.
- [x] 3.2 Atualizar `scripts/editar_imagens.py` para utilizar o novo widget, mantendo a funcionalidade autônoma.
- [x] 3.3 Adicionar testes de regressão em `scripts/editar_imagens_test.py` para validar a execução via CLI.

## 4. Validação Final e Limpeza

- [x] 4.1 Realizar refatoração de código no widget e na janela principal para manter a simplicidade e clareza (Princípio V).
- [x] 4.2 Verificar cobertura de testes e garantir que não há regressões nas funcionalidades originais de edição.
