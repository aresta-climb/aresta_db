# Design Técnico: Controle Total do Editor Aresta via MCP

## Context

O Editor Aresta é uma aplicação desktop multiplataforma (Windows, macOS e Linux Flatpak) desenvolvida em PySide6 estruturada sob uma arquitetura MVC rigorosa validada por [`editor/arquitetura_mvc_test.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/arquitetura_mvc_test.py):
- **`models/`**: O [`CroquiModel`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/models/croqui_model.py) encapsula a árvore de dados Protobuf (`Croqui`), expõe métodos somente-leitura, sinais reativos Qt e mantém o [`IndiceUidsModel`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/models/indice_uids_model.py) sincronizado com lookup $O(1)$ de entidades por `uid` (NanoID 14c).
- **`commands/`**: A camada de comandos ([`comandos_protobuf.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/commands/comandos_protobuf.py) e [`comandos_mapas.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/commands/comandos_mapas.py)) concentra todas as mutações através de subclasses de `ComandoEditor` (`QUndoCommand`). Pela Regra 3 de `arquitetura_mvc_test.py`, apenas `controllers/` e `commands/` podem instanciar classes `Cmd*`.
- **`controllers/`**: [`CroquiController`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/controllers/croqui_controller.py) e [`MapasController`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/controllers/mapas_controller.py) orquestram mutações semânticas e topológicas (POIs, curvas Catmull-Rom e referências por `alvo_uid` e `pontos_uids`).
- **`core/historico.py`**: O [`GerenciadorHistorico`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/historico.py) gerencia o `QUndoStack` e a sincronização append-only com o diário de recuperação (`diario_pendente.bin`).
- **Pipeline de Salvamento e Compilação em RAM**: O salvamento do editor utiliza `CroquiModel.extrair_arquivos_e_serializar` com C LibYAML ([`editor/core/serializacao_util.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/serializacao_util.py)) e compila em memória via `workspace.salvar_e_compilar`, registrando diagnósticos em `CompilacaoLog`.
- **Servidor HTTP Existente**: O grupo `editor` do `pyproject.toml` já inclui `fastapi`, `uvicorn` e `httpx` (utilizados em [`servidor_celular.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/servidor_celular.py)).

Ver motivação detalhada em `proposal.md`.

## Goals / Non-Goals

**Goals:**
- Prover um servidor MCP JSON-RPC 2.0 embutido no processo do editor usando `fastapi` e `uvicorn` (zero dependências externas novas) operando em `127.0.0.1` na porta padrão `27378` (com fallback dinâmico e descoberta via `mcp_sessao.json`).
- Prover um script ponte leve (`python -m editor.mcp.bridge`) operando via `stdio` para clientes que iniciam subprocessos locais (Antigravity, Codex, Claude Desktop).
- Prover o diálogo `DialogoConexaoMcp` na interface do editor com indicador de status e botões para copiar a configuração pronta para os principais agentes de IA.
- Garantir segurança de concorrência com um despachante thread-safe (`DespachanteQt`) que delega execuções de ferramentas para a thread principal da GUI Qt.
- Expor ferramentas MCP com mapeamento 1:1 despachadas exclusivamente via `CroquiController` e `MapasController` (respeitando `arquitetura_mvc_test.py`), com endereçamento híbrido ancorado em `UID` (`IndiceUidsModel`) e caminho relativo/posicional.
- Oferecer ferramentas de visão multimodal (`aresta_capturar_canvas`) e inspeção estrutural (`aresta_obter_arvore`, `aresta_obter_selecao_atual`).
- Oferecer ferramentas de ciclo de vida e workspace reutilizando o pipeline unificado de salvamento/compilação em RAM, histórico (`undo`/`redo`) e foco visual na UI (`aresta_focar_elemento`).
- Cumprir integralmente as diretrizes do [`AGENTS.md`](file:///c:/Renato/Devel/aresta-climb/aresta_db/AGENTS.md): espelhamento 1:1 de arquivos `_test.py`, 100% de cobertura comportamental e proibição absoluta de `MagicMock` para código interno.

**Non-Goals:**
- Implementar interface visual de chat (copiloto embutido na janela do editor) nesta fase — adiada para uma mudança futura.
- Migrar ou reescrever as *skills* de extração de PDF nesta mudança — ficará para uma mudança dedicada subsequente após o servidor MCP estar consolidado.
- Expor o servidor MCP para a internet aberta (a comunicação é restrita a loopback local `127.0.0.1`).
- Adicionar pacotes externos novos ao `pyproject.toml` ou `uv.lock`.

## Decisions

### Decisão 1: Implementação Direta do Protocolo MCP sobre FastAPI + httpx (Zero Novas Dependências)
* **Escolha**: O protocolo MCP é baseado em JSON-RPC 2.0 (`initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`, `resources/list`, `resources/read`). O Editor Aresta expõe esses métodos diretamente em um aplicativo FastAPI em segundo plano vinculado a `127.0.0.1` na porta inicial **`27378`** (mnemônico T9 para `A-R-E-S-T`), suportando tanto `POST /mcp` (Streamable HTTP / RPC direto para a ponte `stdio`) quanto `GET /mcp/sse` + `POST /mcp/messages` (transporte SSE).
* **Descoberta de Sessão**: O editor grava a porta ativa e o token de sessão em `obter_diretorio_base_app() / "mcp_sessao.json"` (aceitando também `ARESTA_MCP_PORTA`). A ponte `stdio` (`editor.mcp.bridge`) lê uma linha JSON-RPC do `stdin`, faz `POST /mcp` local e devolve a linha JSON-RPC no `stdout`.
* **Racional**: Evita adicionar o SDK externo `mcp` ao `pyproject.toml`, mantendo os builds de Linux Flatpak, macOS (Intel/ARM) e Windows MSIX intactos e enxutos, além de facilitar 100% de cobertura de testes sem código morto de terceiros.

### Decisão 2: Conformidade MVC Estrita via `CroquiController` e `MapasController`
* **Escolha**: Em conformidade com a Regra 3 de `editor/arquitetura_mvc_test.py`, nenhum módulo dentro de `editor/mcp/` instancia classes `Cmd*` diretamente. O `CroquiController` recebe os métodos `iniciar_grupo_undo`, `finalizar_grupo_undo` (encapsulando `CmdMacro`, idêntico ao `MapasController`) e `alterar_multiplos_repeated_items` (`CmdAlterarMultiplosRepeatedItems`), e todas as ferramentas de `editor/mcp/` invocam apenas os métodos públicos dos controllers.

### Decisão 3: Diálogo Visual `Conectar Agente de IA (MCP)`
* **Escolha**: Adicionar uma ação no menu superior da `JanelaPrincipal` que abre o `DialogoConexaoMcp`. O diálogo mostra o endereço ativo (`http://127.0.0.1:27378/mcp/sse`), o status do servidor e botões de cópia rápida (`QApplication.clipboard()`) com o snippet JSON/TOML exato para **Google Antigravity**, **OpenAI Codex**, **Claude Desktop** e **Cursor**.

### Decisão 4: Despachante Thread-Safe Qt (`DespachanteQt`)
* **Escolha**: Utilizar um objeto `QObject` residente na thread principal da aplicação (ou `QTimer.singleShot(0, ...)`) acoplado a `concurrent.futures.Future` para executar qualquer leitura ou mutação de modelo/UI na thread principal do Qt e devolver o resultado para a corrotina do servidor FastAPI com timeout configurável.

### Decisão 5: Endereçamento Híbrido Ancorado em `UID` (`resolver_alvo_mcp`)
* **Escolha**: Implementar o resolvedor `resolver_alvo_mcp(model, alvo)` em `editor/mcp/resolvedor_alvo.py`:
  1. Se `alvo` corresponde a um `uid` registrado no `IndiceUidsModel` (ex: `"V1StGXR8_Z5jdH"`), localiza a mensagem em $O(1)$ e resolve seu `caminho_msg` canônico. Se for uma `Escalada` e o campo solicitado pertencer à variante ativa (`via_esportiva`, `boulder`, etc.), resolve automaticamente para o sub-objeto ativo quando apropriado.
  2. Se `alvo` inicia com `<uid>.<subcaminho>` (ex: `"V1StGXR8_Z5jdH.mapas.0"`), localiza a entidade base pelo `uid` e navega o restante via `navegar_para_mensagem`.
  3. Se `alvo` é um caminho posicional desde a raiz (`"picos.0"`, `"botoes.0"`, `""`), delega diretamente para `navegar_para_mensagem`.
  4. Sempre que `aresta_adicionar_repeated` criar uma entidade que possua campo `uid` (`Setor`, `Grupo`, `Escalada`, `Botao`, `PontoDeInteresse`), garante o preenchimento imediato via `gerar_uid()` antes de despachar ao controller e retorna `{"uid": novo_uid, "caminho": caminho_gerado}` na resposta da ferramenta.

### Decisão 6: Salvamento e Compilação em Memória RAM
* **Escolha**: As ferramentas `aresta_salvar` e `aresta_compilar` reutilizam o pipeline em memória (`extrair_arquivos_e_serializar` com `cache_md_out` e `corpos_brutos_md_out` + `workspace.salvar_e_compilar`), atualizando o `CompilacaoLog` e retornando a lista estruturada de erros e avisos ao agente.

## Risks / Trade-offs

- **[Conflito de Porta `27378`]** → Mitigação: Busca sequencial automática a partir de `27378` (`27378..27390`) ou porta efêmera livre do SO, persistida em `mcp_sessao.json` e exibida no `DialogoConexaoMcp`.
- **[Segurança em Ambiente Local]** → Mitigação: Servidor escuta exclusivamente em `127.0.0.1` e valida token de sessão local quando configurado.
- **[Regras de Arquitetura MVC]** → Mitigação: Verificação contínua com `pytest editor/arquitetura_mvc_test.py` garantindo zero instanciações de `Cmd*` fora de `controllers/` e `commands/`.

## Migration Plan

1. Estender `CroquiController` com suporte a `CmdMacro` (`iniciar_grupo_undo` / `finalizar_grupo_undo`) e `alterar_multiplos_repeated_items`.
2. Implementar os módulos independentes em `editor/mcp/` com seus respectivos `*_test.py` espelhados 1:1.
3. Implementar `editor/views/dialogos/dialogo_conexao_mcp.py` e `dialogo_conexao_mcp_test.py`.
4. Integrar o arranque automático do servidor MCP e a ação de menu na `JanelaPrincipal` (`editor/legacy_views/area_principal.py`).
5. Documentar a arquitetura e os fluxos de conexão em `docs/mcp.md`.
