## 1. Testes de Integração em Primeiro Lugar

- [x] 1.1 Criar testes de integração em `editor/views/tela_de_abertura_test.py` verificando que a `TelaDeAbertura` invoca a biblioteca de integração com o sistema operacional e define `windowTitle()` como "Editor Aresta"
- [x] 1.2 Criar teste de integração em `editor/main_test.py` verificando a atribuição antecipada do ícone global no `QApplication` durante o startup da função `main()`


## 2. Biblioteca Independente com TDD (Library-First: editor/core/integracao_windows.py)

- [x] 2.1 [Red] Criar o arquivo de testes unitários `editor/core/integracao_windows_test.py` cobrindo os cenários de sucesso no Windows (`WS_EX_APPWINDOW` e `WS_SYSMENU`), tratamento de falhas e comportamento no-op em sistemas não-Windows
- [x] 2.2 [Green] Implementar a biblioteca independente `editor/core/integracao_windows.py` com a função `configurar_presenca_barra_de_tarefas`, tipagem estática e nomes 100% em português brasileiro
- [x] 2.3 [Refactor] Refatorar e assegurar 100% de cobertura de testes unitários no módulo `editor/core/integracao_windows.py`


## 3. Integração na Interface Gráfica e Ciclo de Inicialização

- [x] 3.1 Conectar a chamada de `configurar_presenca_barra_de_tarefas` e `self.setWindowTitle("Editor Aresta")` no construtor da `TelaDeAbertura` (`editor/views/tela_de_abertura.py`)
- [x] 3.2 Atualizar `editor/main.py` para antecipar a definição de `app.setWindowIcon` imediatamente após a criação do `QApplication`



## 4. Validação de Cobertura (100%) e Verificação Final

- [x] 4.1 Executar suíte completa de testes com relatório de cobertura (`pytest --cov`), garantindo 100% de cobertura nos módulos novos e modificados
- [x] 4.2 Executar verificação dos estilos Win32 nativos da janela para assegurar ausência de regressões

