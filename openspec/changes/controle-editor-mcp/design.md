# Design Técnico: Controle Total do Editor Aresta via MCP

## Context

O Editor Aresta é uma aplicação desktop multiplataforma (Windows, macOS e Linux Flatpak) desenvolvida em PySide6 estruturada sob uma arquitetura MVC rigorosa:
- **`models/`**: O [`CroquiModel`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/models/croqui_model.py) encapsula a árvore de dados Protobuf (`Croqui`), expõe métodos somente-leitura, sinais reativos Qt e mantém o [`IndiceUidsModel`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/models/indice_uids_model.py) sincronizado com lookup $O(1)$ de entidades por `uid` (NanoID 14c).
- **`commands/`**: A camada de comandos ([`comandos_protobuf.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/commands/comandos_protobuf.py) e [`comandos_mapas.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/commands/comandos_mapas.py)) concentra todas as mutações através de subclasses de `ComandoEditor` (`QUndoCommand`).
- **`controllers/`**: [`CroquiController`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/controllers/croqui_controller.py) e [`MapasController`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/controllers/mapas_controller.py) orquestram mutações semânticas e topológicas (POIs, curvas Catmull-Rom e referências por `alvo_uid` e `pontos_uids`).
- **`core/historico.py`**: O [`GerenciadorHistorico`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/historico.py) gerencia o `QUndoStack` e a sincronização append-only com o diário de recuperação (`diario_pendente.bin`).
- **`plataforma/` e `core/storage.py`**: [`obter_diretorio_base_app()`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/storage.py#L7) abstrai o diretório de dados do usuário em cada sistema operacional (incluindo o sandbox Flatpak no Linux).
- **Servidor HTTP Existente**: O editor já utiliza FastAPI e Uvicorn (ver [`servidor_celular.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/servidor_celular.py)) em background.

Ver motivação detalhada em `proposal.md`.

## Goals / Non-Goals

**Goals:**
- Prover um servidor MCP embutido no processo do editor via transporte SSE/HTTP local (`127.0.0.1`) na porta padrão `27378` (com fallback dinâmico e descoberta via `mcp_sessao.json`).
- Prover um script ponte leve (`python -m editor.mcp.bridge`) operando via `stdio` para clientes que iniciam subprocessos locais (Antigravity, Codex, Claude Desktop).
- Prover o diálogo `DialogoConexaoMcp` na interface do editor com indicador de status e botões para copiar a configuração pronta para os principais agentes de IA.
- Garantir segurança de concorrência com um despachante thread-safe (`DespachanteQt`) que delega execuções de ferramentas para a thread principal da GUI Qt.
- Expor ferramentas MCP com mapeamento 1:1 para todos os comandos `Cmd*` e operações do `MapasController`, com endereçamento híbrido ancorado em `UID` (`IndiceUidsModel`) e caminho relativo/posicional.
- Oferecer ferramentas de visão multimodal (`aresta_capturar_canvas`) e inspeção estrutural (`aresta_obter_arvore`, `aresta_obter_selecao_atual`).
- Oferecer ferramentas de ciclo de vida e workspace: abertura/status de croqui, compilação/validação, salvamento, histórico (`undo`/`redo`) e foco visual na UI (`aresta_focar_elemento`).
- Cumprir integralmente as diretrizes do [`AGENTS.md`](file:///c:/Renato/Devel/aresta-climb/aresta_db/AGENTS.md): espelhamento 1:1 de arquivos `_test.py`, 100% de cobertura comportamental e proibição absoluta de `MagicMock` para código interno.

**Non-Goals:**
- Implementar interface visual de chat (copiloto embutido na janela do editor) nesta fase — adiada para uma mudança futura.
- Migrar ou reescrever as *skills* de extração de PDF nesta mudança — ficará para uma mudança dedicada subsequente após o servidor MCP estar consolidado.
- Expor o servidor MCP para a internet aberta (a comunicação é restrita a loopback local `127.0.0.1`).
- Criar comandos de mutação direta que ignorem a pilha de histórico `QUndoStack`.

## Decisions

### Decisão 1: Transporte Híbrido, Porta `27378` e Descoberta Multiplataforma
* **Escolha**: O Editor Aresta roda um servidor FastAPI/Starlette com endpoint `/mcp/sse` em segundo plano vinculado a `127.0.0.1`. A porta inicial padrão é **`27378`** (mnemônico T9 para `A-R-E-S-T`, fora de faixas comumente ocupadas como `8000`, `8080` ou `8765`). Caso `27378` esteja em uso, o servidor busca automaticamente a próxima porta livre (`27379+`).
* **Descoberta de Sessão**: O editor grava a porta ativa e um token de sessão em `obter_diretorio_base_app() / "mcp_sessao.json"` (além de aceitar override via variável de ambiente `ARESTA_MCP_PORTA`). A ponte `stdio` (`editor.mcp.bridge`) lê `mcp_sessao.json` (ou tenta `127.0.0.1:27378` diretamente como fallback caso o editor esteja em sandbox isolado) e encaminha o tráfego JSON-RPC.
* **Alternativas consideradas**:
  - *Porta 8765 ou 8080*: Muito utilizadas por servidores de desenvolvimento e ferramentas locais, gerando colisões frequentes.
  - *Caminho fixo `~/.aresta/`*: Incompatível com a padronização multiplataforma de `editor/plataforma/` e com o sandbox do Flatpak no Linux.

### Decisão 2: Diálogo Visual `Conectar Agente de IA (MCP)`
* **Escolha**: Adicionar uma ação no menu superior da `JanelaPrincipal` que abre o `DialogoConexaoMcp`. O diálogo mostra o endereço ativo (`http://127.0.0.1:27378/mcp/sse`), o status do servidor e abas/botões de cópia rápida (`QApplication.clipboard()`) com o snippet JSON/TOML exato para **Google Antigravity**, **OpenAI Codex**, **Claude Desktop** e **Cursor**.
* **Racional**: Elimina o atrito de configuração manual de caminhos pelo usuário.

### Decisão 3: Despachante Thread-Safe Qt (`DespachanteQt`)
* **Escolha**: Utilizar um objeto `QObject` residente na thread principal da aplicação (ou `QTimer.singleShot(0, ...)`) acoplado a `concurrent.futures.Future` para executar qualquer leitura ou mutação de modelo/UI na thread principal do Qt e devolver o resultado para a corrotina do servidor FastAPI/MCP com timeout configurável.

### Decisão 4: Endereçamento Híbrido Ancorado em `UID` (`resolver_alvo_mcp`)
* **Escolha**: Implementar o resolvedor `resolver_alvo_mcp(model, alvo)` em `editor/mcp/resolvedor_alvo.py`:
  1. Se `alvo` corresponde a um `uid` registrado no `IndiceUidsModel` (ex: `"V1StGXR8_Z5jdH"`), localiza a mensagem em $O(1)$ e resolve seu `caminho_msg` canônico. Se for uma `Escalada` e o campo solicitado pertencer à variante ativa (`via_esportiva`, `boulder`, etc.), resolve automaticamente para o sub-objeto ativo quando apropriado.
  2. Se `alvo` inicia com `<uid>.<subcaminho>` (ex: `"V1StGXR8_Z5jdH.mapas.0"`), localiza a entidade base pelo `uid` e navega o restante via `navegar_para_mensagem`.
  3. Se `alvo` é um caminho posicional desde a raiz (`"picos.0"`, `"botoes.0"`, `""`), delega diretamente para `navegar_para_mensagem`.
  4. Sempre que `aresta_adicionar_repeated` criar uma entidade que possua campo `uid` (`Setor`, `Grupo`, `Escalada`, `Botao`, `PontoDeInteresse`), garante o preenchimento imediato via `gerar_uid()` antes de empilhar o comando e retorna `{"uid": novo_uid, "caminho": caminho_gerado}` na resposta da ferramenta.

### Decisão 5: Captura Multimodal do Canvas (`aresta_capturar_canvas`)
* **Escolha**: Capturar o widget solicitado (`"mapa"`, `"foto"`, `"dados"` ou `"janela"`) na thread principal via `QWidget.grab()` / `QPixmap`, redimensionar opcionalmente para manter orçamento de tokens enxuto e codificar em PNG Base64 no formato `ImageContent` do protocolo MCP.

### Decisão 6: Testes Comportamentais 1:1 sem Mocks Internos
* **Escolha**: Em conformidade com o Princípio V do `AGENTS.md`, todos os testes de `editor/mcp/*_test.py` instanciam `CroquiModel`, `GerenciadorHistorico`, `CroquiController`, `MapasController` e objetos Protobuf reais sobre `tmp_path`, exercitando o fluxo real de ponta a ponta (incluindo `undo()` e `redo()`).

## Risks / Trade-offs

- **[Conflito de Porta `27378`]** → Mitigação: Busca sequencial automática a partir de `27378` (`27378..27390`) ou porta efêmera livre do SO, persistida em `mcp_sessao.json` e exibida no `DialogoConexaoMcp`.
- **[Segurança em Ambiente Local]** → Mitigação: Servidor escuta exclusivamente em `127.0.0.1` e valida token de sessão local quando aplicável.
- **[Operações de Compilação Pesadas]** → Mitigação: `aresta_compilar` executa a validação e retorna os diagnósticos estruturados sem travar o loop de eventos.

## Migration Plan

1. Adicionar o pacote `mcp` ao grupo de dependências `editor` no `pyproject.toml`.
2. Implementar os módulos independentes em `editor/mcp/` com seus respectivos `*_test.py` espelhados 1:1.
3. Implementar `editor/views/dialogos/dialogo_conexao_mcp.py` e `dialogo_conexao_mcp_test.py`.
4. Integrar o arranque automático do servidor MCP e a ação de menu na `JanelaPrincipal` (`editor/legacy_views/area_principal.py`).
5. Documentar a arquitetura e os fluxos de conexão em `docs/mcp.md`.
