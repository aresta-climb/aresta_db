## 1. Testes de Prevenção de Regressão de Tema Claro e Contraste (TDD)

- [x] 1.1 Criar teste unitário em `editor/views/estilo_test.py` verificando a função `configurar_tema_claro_aplicacao` garantindo a imposição do esquema claro (`ColorScheme.Light`).
- [x] 1.2 Criar teste unitário em `editor/legacy_views/tela_de_carregamento_test.py` validando que os botões de ação e títulos de grupo possuem cor de texto explícita e escopo apropriado.
- [x] 1.3 Criar teste em `editor/main_test.py` validando que o ambiente e a aplicação configuram o tema claro na inicialização.


## 2. Implementação do Forçamento de Tema Claro e Higiene de QSS

- [x] 2.1 Implementar `configurar_tema_claro_aplicacao` em `editor/views/estilo.py`.
- [x] 2.2 Configurar `QT_QPA_PLATFORM="windows:darkmode=0"` e invocar `configurar_tema_claro_aplicacao` em `editor/main.py`.
- [x] 2.3 Ajustar as folhas de estilo de `TelaDeCarregamento` em `editor/legacy_views/tela_de_carregamento.py` para definir cores explícitas e escopar botões principais.

## 3. Verificação e Validação da Suíte de Testes

- [x] 3.1 Executar os novos testes unitários e de integração garantindo que passam (Green).
- [x] 3.2 Executar a suíte de testes completa do editor para assegurar ausência de regressões.


