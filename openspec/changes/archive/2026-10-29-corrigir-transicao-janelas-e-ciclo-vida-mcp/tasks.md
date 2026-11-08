# Tasks

## 1. Inicialização do ServidorMCP sem Bombeamento de Eventos Qt

- [x] 1.1 Escrever teste em `editor/mcp/servidor_test.py` verificando que `ServidorMCP.iniciar()` sobe o servidor HTTP em segundo plano sem disparar `app.aboutToQuit` mesmo quando chamado em um momento em que todas as janelas da `QApplication` acabaram de ser ocultadas (`lastWindowClosed` pendente), e confirmar que o teste falha antes da correção (Red)
- [x] 1.2 Remover `QCoreApplication.processEvents()` do laço de espera de `ServidorMCP.iniciar()` em `editor/mcp/servidor.py` e validar que `uv run pytest editor/mcp/servidor_test.py` passa com 100% de cobertura (Green)

## 2. Compartilhamento Contínuo do ServidorMCP e Blindagem de Transições de Janela

- [x] 2.1 Escrever testes de integração reais em `editor/main_test.py` (sem mocks para diálogos ou janelas internas) reproduzindo dentro de `app.exec()` a transição `TelaDeAbertura` -> `TelaDeCarregamento` -> importação/abertura de croqui oficial -> `JanelaPrincipal` -> retorno via `"Abrir Novo"`, verificando que a `JanelaPrincipal` permanece aberta e viva no loop de eventos e que a mesma instância e porta de `ServidorMCP` são mantidas do início ao fim, e confirmar que falham antes da implementação (Red)
- [x] 2.2 Atualizar `JanelaPrincipal` (`editor/legacy_views/area_principal.py`) e `TelaDeCarregamento` (`editor/legacy_views/tela_de_carregamento.py`) para aceitar e reutilizar uma instância compartilhada de `ServidorMCP` sem encerrá-la ao alternar entre a `JanelaPrincipal` e a `TelaDeCarregamento` (`"Abrir Novo"`), validando com `uv run pytest editor/legacy_views/tela_de_carregamento_test.py editor/legacy_views/area_principal_test.py`
- [x] 2.3 Atualizar `ControladorAplicativo` (`editor/main.py`) para gerenciar o ciclo de vida único do `ServidorMCP` compartilhado (iniciando-o ao abrir a `TelaDeCarregamento`, injetando-o na `JanelaPrincipal` e encerrando-o apenas na saída real da aplicação) e proteger as transições `executar_selecao()` / `mostrar_janela_principal()` contra `quitOnLastWindowClosed`, validando que todos os testes em `uv run pytest editor/main_test.py` passam (Green)

## 3. Verificação Integrada e Qualidade

- [x] 3.1 Executar a suíte de testes completa dos módulos afetados (`uv run pytest editor/main_test.py editor/mcp/servidor_test.py editor/legacy_views/tela_de_carregamento_test.py editor/legacy_views/area_principal_test.py`) e os verificadores de qualidade (`uv run ruff check` e `uv run mypy`), garantindo zero erros e conformidade integral com o `AGENTS.md`
