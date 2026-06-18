## 1. Testes de Integração em Primeiro Lugar

- [x] 1.1 Criar o arquivo `editor/controllers/compilacao_integracao_test.py` para escrever os testes de integração do Controller conversando com o Model e coordenando uma "View Mock", estabelecendo o contrato e a fronteira entre as partes (Princípio V).

## 2. TDD Rigoroso (Model e Controller)

- [x] 2.1 Criar `editor/models/compilacao_log_test.py` com testes exaustivos para o armazenamento e estado do modelo.
- [x] 2.2 Implementar `editor/models/compilacao_log.py` alcançando a meta de **100% de unit test coverage**.
- [x] 2.3 Criar `editor/controllers/compilacao_controller_test.py` focado na lógica isolada do controlador, categorização de log e formatação HTML.
- [x] 2.4 Implementar `editor/controllers/compilacao_controller.py` garantindo que todos os testes passem (inclusive o teste de integração) e que atinja **100% de coverage**. Todos nomes e comentários devem ser em português brasileiro.

## 3. TDD Rigoroso (View)

- [x] 3.1 Criar `editor/views/widget_saida_compilacao_test.py` testando de forma unitária se a formatação (ex: textuais pasteis) e os componentes visuais são manipulados corretamente através dos métodos expostos para o Controller.
- [x] 3.2 Implementar `editor/views/widget_saida_compilacao.py` de forma declarativa e simples (anti-abstração), focando apenas na exibição. Assegurar **100% de coverage**.

## 4. Integração Simples na Janela Principal

- [x] 4.1 Atualizar `editor/legacy_views/area_principal_test.py` para validar a substituição do `DialogoErrosCompilacao` pelo novo fluxo MVC sem interromper o salvamento.
- [x] 4.2 Em `editor/legacy_views/area_principal.py`, remover `DialogoErrosCompilacao`, instanciar o `CompilacaoController` com o `WidgetSaidaCompilacao` e amarrá-lo na `BottomDockWidgetArea`. Repassar o log da compilação para o Controller de forma limpa.
- [x] 4.3 Rodar toda a suíte de testes usando `pytest --cov` na pasta `editor` para confirmar que nenhum coverage caiu e que a nova meta de 100% sobre as novas classes se mantém sólida.
