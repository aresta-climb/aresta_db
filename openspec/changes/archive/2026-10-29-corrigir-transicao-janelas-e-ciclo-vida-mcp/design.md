# Design

## Context

Conforme detalhado em `proposal.md`, o fluxo padrão do Editor Aresta (`ControladorAplicativo` em `editor/main.py`) transiciona entre três janelas de nível superior (`TelaDeAbertura` -> `TelaDeCarregamento` -> `JanelaPrincipal`).

Existem dois problemas acoplados na implementação atual:
1. **Encerramento prematuro do loop de eventos Qt (`app.exec()`)**:
   - Quando `TelaDeCarregamento.accept()` é chamado (após importar um croqui oficial, criar um novo croqui ou escolher um item do histórico), `QDialog.done(Accepted)` oculta imediatamente o diálogo.
   - Nesse instante, há **zero janelas visíveis** na aplicação (`TelaDeAbertura` já foi fechada e `JanelaPrincipal` ainda será construída em `mostrar_janela_principal()`).
   - Com `quitOnLastWindowClosed=True` (padrão do Qt), o fechamento da `TelaDeCarregamento` emite `lastWindowClosed` e agenda a verificação de saída do `QApplication`.
   - Em seguida, `JanelaPrincipal.__init__()` é executado **antes** de `self.janela_principal.show()` e chama `self.iniciar_servidor_mcp()` -> `ServidorMCP.iniciar()`, que executava um laço `while not self._server.started: QCoreApplication.processEvents()`.
   - Ao processar eventos com zero janelas visíveis, o Qt dispara `aboutToQuit` e encerra `app.exec()` com código `0` antes mesmo de `JanelaPrincipal.show()` ser alcançado.
2. **Ciclo de vida fragmentado do `ServidorMCP`**:
   - Embora a especificação `editor-controle-mcp` previsse o `ServidorMCP` ativo desde a `TelaDeCarregamento` e compartilhado com a `JanelaPrincipal`, `ControladorAplicativo` não instanciava nem injetava um `ServidorMCP` compartilhado.
   - Assim, `TelaDeCarregamento` só iniciava um servidor se o usuário clicasse no botão `"Conectar Agente de IA (MCP)..."`, e `JanelaPrincipal` instanciava outro `ServidorMCP` do zero (e o destruía ao clicar em `"Abrir Novo"`).

## Goals / Non-Goals

**Goals:**
- Garantir que o loop principal do Qt (`app.exec()`) nunca seja encerrado durante transições controladas entre `TelaDeAbertura`, `TelaDeCarregamento` e `JanelaPrincipal`.
- Manter uma única instância primária de `ServidorMCP` gerenciada pelo `ControladorAplicativo` durante toda a execução da aplicação, compartilhando-a entre `TelaDeCarregamento` e `JanelaPrincipal` sem reinicializar o socket/Uvicorn na transição.
- Remover `QCoreApplication.processEvents()` do laço de inicialização da thread Uvicorn em `ServidorMCP.iniciar()`.
- Garantir cobertura por teste de integração real com `app.exec()` e objetos Qt reais (`TelaDeAbertura`, `TelaDeCarregamento`, `JanelaPrincipal` e `ServidorMCP`), sem mocks para classes internas (Princípio V do `AGENTS.md`).

**Non-Goals:**
- Alterar o protocolo JSON-RPC/SSE ou os contratos das ferramentas MCP existentes.
- Alterar o comportamento de janelas secundárias (`janelas_secundarias`), nas quais um segundo croqui aberto simultaneamente em paralelo continua tendo sua própria instância de `JanelaPrincipal` e sessão MCP secundária registrada em `mcp_sessoes.json`.

## Decisions

### 1. Propriedade e Compartilhamento do `ServidorMCP` Primário no `ControladorAplicativo`

- **Decisão**: O `ControladorAplicativo` mantém `self.despachante_mcp: DespachanteQt` (vinculado à `QApplication` / thread principal) e `self.servidor_mcp: ServidorMCP | None`.
  - Ao entrar em `executar_selecao()`, o `ControladorAplicativo` passa `servidor_mcp=self.servidor_mcp` para `TelaDeCarregamento` e chama `self.servidor_mcp = self.tela_carregamento.garantir_servidor_mcp(iniciar_rede=True)`.
  - Como `DespachanteQt` só precisa pertencer à thread principal da GUI (e não a um widget específico que será fechado), o `DespachanteQt` do `ServidorMCP` compartilhado permanece válido durante toda a vida do `QApplication`.
  - Na `TelaDeCarregamento`, `garantir_servidor_mcp()` configura `croqui_aberto=False`, registra as ferramentas de conhecimento e gestão de croquis (`aresta_listar_croquis`, `aresta_abrir_croqui_existente`, `aresta_importar_croqui_oficial`, `aresta_criar_novo_croqui`) e garante que o servidor esteja iniciado na porta `27378`.
  - Ao transicionar para `mostrar_janela_principal()`, o `ControladorAplicativo` passa `servidor_mcp=self.servidor_mcp` para `JanelaPrincipal(..., servidor_mcp=self.servidor_mcp, iniciar_mcp=True)`.
  - A `JanelaPrincipal` recebe `servidor_mcp` no construtor: quando recebe uma instância externa compartilhada (`_servidor_mcp_compartilhado = True`), ela reutiliza essa instância, registra as ferramentas do croqui carregado e atualiza `definir_croqui_ativo(id_croqui, caminho_db, croqui_aberto=True)`.
  - Quando o usuário clica em `"Abrir Novo"` (`_concluir_abrir_novo`), a `JanelaPrincipal` **não** para o `servidor_mcp` se ele for compartilhado (`_servidor_mcp_compartilhado=True`); a `TelaDeCarregamento` subsequente assume novamente o mesmo `self.servidor_mcp` e redefine `definir_croqui_ativo("", croqui_aberto=False)`.
  - Quando a aplicação realmente encerra (sinal `app.aboutToQuit` ou saída por cancelamento da `TelaDeCarregamento`), o `ControladorAplicativo` chama `self.encerrar_servidor_mcp()`.
- **Alternativa considerada**: Parar o `ServidorMCP` da `TelaDeCarregamento` e iniciar um novo `ServidorMCP` na `JanelaPrincipal`.
  - *Descartada*: Causa queda de conexões SSE ativas de agentes durante a abertura do croqui, exige novo bind de porta a cada troca de croqui e contraria o requisito da spec `editor-controle-mcp`.

### 2. Blindagem das Transições de Janela contra `quitOnLastWindowClosed`

- **Decisão**: Combinar duas proteções complementares:
  1. Em `ServidorMCP.iniciar()`, remover `QCoreApplication.processEvents()` do laço `while not self._server.started and time.monotonic() < prazo:`. Como o `uvicorn.Server` inicializa seu socket puramente em uma `threading.Thread` Python (sem depender da fila de eventos do Qt), aguardar com `time.sleep(0.01)` é suficiente e elimina qualquer reentrância do loop de eventos da GUI durante `__init__()`.
  2. Em `ControladorAplicativo.executar_selecao()` e `mostrar_janela_principal()`, manter `self.app.setQuitOnLastWindowClosed(False)` durante as transições controladas de janela (ou manter um `QEventLoopLocker` ativo durante a transição até depois de `self.janela_principal.show()`), restaurando `self.app.setQuitOnLastWindowClosed(True)` somente após a janela destino estar visível na tela.
- **Alternativa considerada**: Desativar `quitOnLastWindowClosed` permanentemente durante toda a execução.
  - *Descartada*: Se `quitOnLastWindowClosed` ficar `False` permanentemente enquanto a `JanelaPrincipal` está aberta, fechar a `JanelaPrincipal` pelo botão `X` do sistema operacional não encerraria o `app.exec()` automaticamente a menos que gerenciássemos manualmente a contagem de todas as janelas abertas. Proteger a flag durante as transições em `executar_selecao()` / `mostrar_janela_principal()` preserva o comportamento nativo do Qt quando o usuário fecha a última `JanelaPrincipal` no `X`.

### 3. Reconciliação de `abrir_croqui_via_mcp` quando `TelaDeCarregamento.exec()` Está Ativo

- **Decisão**: Quando a `TelaDeCarregamento` está aberta em `resultado = self.tela_carregamento.exec()` dentro de `ControladorAplicativo.executar_selecao()`, o callback de abertura via MCP (`TelaDeCarregamento._abrir_croqui_via_mcp`) define `self.caminho_croqui_selecionado = caminho` e chama `self.accept()`. Isso já faz `self.tela_carregamento.exec()` retornar `QDialog.DialogCode.Accepted` e invocar `self.mostrar_janela_principal()` naturalmente! E quando `ControladorAplicativo.abrir_croqui_via_mcp()` é chamado com uma `JanelaPrincipal` já aberta (`self.janela_principal is not None`), ele instancia uma nova `JanelaPrincipal` em `self.janelas_secundarias` (que cria seu próprio `ServidorMCP` na porta seguinte `27379+`).

## Risks / Trade-offs

- **[Risco] Vazamento de thread Uvicorn em testes que instanciam `ControladorAplicativo` ou `TelaDeCarregamento`** → **Mitigação**: Permitir desativar ou encerrar o `servidor_mcp` no teardown/fechamento do controlador (`controlador.encerrar_servidor_mcp()` conectado também a `app.aboutToQuit`) e usar `diretorio_sessao_mcp` isolado em `tmp_path` nos testes de integração.
- **[Risco] DespachanteQt vinculado a um QDialog destruído** → **Mitigação**: Ao criar o `ServidorMCP` no `ControladorAplicativo` (ou em `TelaDeCarregamento.garantir_servidor_mcp`), instanciar `DespachanteQt()` sem `parent` de diálogo efêmero (vinculado à thread principal da aplicação), evitando que a destruição de `TelaDeCarregamento` invalide o `QObject` do despachante.
