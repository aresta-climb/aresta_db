# Proposal

## Why

Ao importar um croqui oficial, criar um novo croqui ou abrir um croqui existente a partir da `TelaDeCarregamento` no fluxo padrão do Editor Aresta (`uv run editor/main.py`), o aplicativo encerra silenciosamente (`exit(0)`) sem registrar nenhum erro. Isso ocorre porque `TelaDeCarregamento.accept()` oculta a única janela visível antes da exibição da `JanelaPrincipal`, armando o gatilho `quitOnLastWindowClosed` do Qt; em seguida, o construtor `JanelaPrincipal.__init__` instancia um novo `ServidorMCP` e executa `QCoreApplication.processEvents()` enquanto ainda há zero janelas visíveis, fazendo o Qt disparar `aboutToQuit` e encerrar o loop principal `app.exec()`. Além disso, o servidor MCP estava sendo recriado entre a `TelaDeCarregamento` e a `JanelaPrincipal`, em vez de permanecer como uma única instância contínua durante todo o ciclo de vida da aplicação.

## What Changes

- **Preservação do Loop de Eventos Qt nas Transições de Janela (`ControladorAplicativo`)**: Garantir que transições entre `TelaDeAbertura`, `TelaDeCarregamento` e `JanelaPrincipal` (tanto na abertura inicial quanto ao acionar "Abrir Novo") nunca acionem o encerramento automático por falta temporária de janelas visíveis (`quitOnLastWindowClosed` / `QEventLoopLocker`).
- **Instância Única e Contínua do `ServidorMCP` no `ControladorAplicativo`**: Iniciar e manter uma única instância primária de `ServidorMCP` no `ControladorAplicativo`, injetando-a na `TelaDeCarregamento` (já ativa na abertura do diálogo com `croqui_aberto=False`) e reaproveitando essa mesma instância na `JanelaPrincipal` primária (atualizando `croqui_aberto=True`, `id_croqui` e registrando as ferramentas do modelo sem derrubar a porta `27378` ou conexões ativas). Ao retornar para a `TelaDeCarregamento` ("Abrir Novo"), a `JanelaPrincipal` primária não encerra o servidor compartilhado, que volta ao estado `croqui_aberto=False` até o encerramento real do aplicativo.
- **Remoção de `QCoreApplication.processEvents()` da Espera de Boot do Uvicorn (`ServidorMCP.iniciar`)**: No laço de espera pelo início da thread independente do `uvicorn.Server`, aguardar apenas com `time.sleep(0.01)` sem bombear eventos da interface gráfica Qt durante construtores de janelas.
- **Teste de Integração Real Fim-a-Fim do Ciclo de Vida (`editor/main_test.py`)**: Adicionar testes de integração reais (sem `MagicMock` para janelas ou diálogos internos) exercitando `app.exec()`, a transição `TelaDeAbertura` -> `TelaDeCarregamento` -> importação de croqui oficial -> `JanelaPrincipal` e a continuidade da mesma instância de `ServidorMCP`, comprovando que `aboutToQuit` não é disparado prematuramente e que a `JanelaPrincipal` permanece aberta e responsiva.

## Capabilities

### New Capabilities

<!-- Nenhuma nova capability; os requisitos pertencem às capabilities existentes abaixo. -->

### Modified Capabilities

- `editor-inicializacao`: Fortalece o requisito de transição entre `TelaDeAbertura`, `TelaDeCarregamento` e `JanelaPrincipal` para garantir que o loop de eventos principal (`app.exec()`) permaneça ativo durante todas as transições de janela até o encerramento explícito pelo usuário.
- `editor-controle-mcp`: Especifica que a instância primária do `ServidorMCP` pertence ao ciclo de vida do aplicativo (`ControladorAplicativo`), iniciando automaticamente ao exibir a `TelaDeCarregamento` e sendo compartilhada continuamente com a `JanelaPrincipal` sem reinicialização de porta ou bombeamento de eventos Qt no construtor.

## Impact

- `editor/main.py` (`ControladorAplicativo`): Gerenciamento do `ServidorMCP` compartilhado, proteção contra `quitOnLastWindowClosed` durante transições de janelas e encerramento limpo no `aboutToQuit` / saída do aplicativo.
- `editor/legacy_views/area_principal.py` (`JanelaPrincipal`): Suporte a receber uma instância `servidor_mcp` compartilhada do `ControladorAplicativo` (preservando-a ao voltar para a seleção via "Abrir Novo" e encerrando apenas quando a janela for dona exclusiva do servidor ou no fechamento definitivo).
- `editor/legacy_views/tela_de_carregamento.py` (`TelaDeCarregamento`): Reutilização do `servidor_mcp` injetado pelo `ControladorAplicativo` com ativação imediata das ferramentas de gestão de croquis.
- `editor/mcp/servidor.py` (`ServidorMCP.iniciar`): Remoção do `QCoreApplication.processEvents()` no laço de espera da thread do Uvicorn.
- `editor/main_test.py` e `editor/mcp/servidor_test.py`: Novos testes de integração real com `app.exec()` reproduzindo o fluxo de importação/abertura de croqui oficial e validando a permanência da `JanelaPrincipal` e da mesma sessão MCP.
