# Tasks

## 1. Infraestrutura, Despacho Thread-Safe e Resolução por UID

- [x] 1.1 Adicionar suporte a `iniciar_grupo_undo`, `finalizar_grupo_undo` (`CmdMacro`) e `alterar_multiplos_repeated_items` em `editor/controllers/croqui_controller.py` com testes em `editor/controllers/croqui_controller_test.py`
- [x] 1.2 Implementar a classe `DespachanteQt` em `editor/mcp/despachante.py` com testes comportamentais em `editor/mcp/despachante_test.py` cobrindo execução na thread principal, propagação de exceções e timeouts
- [x] 1.3 Implementar o gerenciador de sessão local multiplataforma em `editor/mcp/sessao.py` (porta padrão `27378`, fallback automático e persistência em `obter_diretorio_base_app() / "mcp_sessao.json"`) com testes em `editor/mcp/sessao_test.py`
- [x] 1.4 Implementar o resolvedor de alvos híbrido (`resolver_alvo_mcp` por `UID` do `IndiceUidsModel`, `<uid>.<subcaminho>` e caminho posicional) em `editor/mcp/resolvedor_alvo.py` com testes comportamentais reais em `editor/mcp/resolvedor_alvo_test.py`

## 2. Servidor MCP JSON-RPC/SSE e Transporte Híbrido

- [x] 2.1 Implementar o servidor JSON-RPC 2.0 sobre HTTP/SSE local em `editor/mcp/servidor.py` utilizando FastAPI vinculado a `127.0.0.1:27378` (com fallback de porta livre e suporte a `POST /mcp`, `GET /mcp/sse` e `POST /mcp/messages`) e testes em `editor/mcp/servidor_test.py`
- [x] 2.2 Implementar a ponte CLI `editor/mcp/bridge.py` operando via `stdio` com testes em `editor/mcp/bridge_test.py` verificando a descoberta via `mcp_sessao.json` e o encaminhamento bidirecional de mensagens JSON-RPC

## 3. Catálogo Inicial de Ferramentas, Visão e Ciclo de Vida

- [x] 3.1 Implementar as ferramentas iniciais de mutação em `editor/mcp/ferramentas_comandos.py` despachando via `CroquiController` e `MapasController` com testes em `editor/mcp/ferramentas_comandos_test.py`
- [x] 3.2 Implementar `aresta_capturar_canvas`, `aresta_obter_arvore` e `aresta_obter_selecao_atual` em `editor/mcp/ferramentas_visao.py` com testes em `editor/mcp/ferramentas_visao_test.py`
- [x] 3.3 Implementar `aresta_compilar`, `aresta_salvar`, `aresta_desfazer`, `aresta_refazer`, `aresta_focar_elemento` e `aresta_status_workspace` em `editor/mcp/ferramentas_ciclo_vida.py` com testes em `editor/mcp/ferramentas_ciclo_vida_test.py`
- [x] 3.4 Implementar `DialogoConexaoMcp` em `editor/views/dialogos/dialogo_conexao_mcp.py`, integrar à `JanelaPrincipal` (`editor/legacy_views/area_principal.py`) e documentar em `docs/mcp.md`

## 4. Blindagem Defensiva do Histórico, Comandos Canônicos e Controller

- [x] 4.1 Blindar `GerenciadorHistorico` em `editor/core/historico.py` adicionando `@Slot(int)` explícito em `_on_index_changed` e proteção em `__getattr__` contra atributos privados/internos (`startswith("_")`), com testes comportamentais em `editor/core/historico_test.py`
- [x] 4.2 Blindar `CmdAlterarCampo.__init__` em `editor/commands/comandos_protobuf.py` para rejeitar *fail-fast* campos `repeated` sem índice (`field_desc.is_repeated`) e validar a compatibilidade de tipo de `valor_novo` com o `FieldDescriptor` antes de `QUndoStack.push`, com testes em `editor/commands/comandos_protobuf_test.py`
- [x] 4.3 Adicionar o método canônico `alterar_campo` em `editor/controllers/croqui_controller.py` aceitando alteração de campo único ou lote `campos: dict[str, Any]` (instanciando todos os `CmdAlterarCampo` previamente e agrupando em `CmdMacro` quando houver múltiplos campos), com testes em `editor/controllers/croqui_controller_test.py`

## 5. Simplificação Canônica das Ferramentas MCP e Coerção JSON-Protobuf

- [x] 5.1 Unificar `editor/mcp/resolvedor_alvo.py` com `navegar_para_alvo` de `comandos_protobuf.py` e atualizar `editor/mcp/resolvedor_alvo_test.py`
- [x] 5.2 Refatorar `editor/mcp/ferramentas_comandos.py` para expor a interface canônica do `CroquiController` (`aresta_alterar_campo` com suporte a campo único ou lote `campos`, coerção de `dict` -> `Message` via `ParseDict` e nomes de `Enum` -> `int`; retorno de `tamanho` atualizado em `aresta_adicionar_repeated`/`aresta_remover_repeated`; remoção de `aresta_iniciar_macro`/`aresta_finalizar_macro` e das tools antigas fragmentadas), atualizando `editor/mcp/ferramentas_comandos_test.py`

## 6. Inspeção de Coleções Repeated e Exposição de Schema Protobuf e Skills

- [x] 6.1 Evoluir `aresta_obter_arvore` em `editor/mcp/ferramentas_visao.py` para aceitar o parâmetro opcional `campo` (suportando leitura direta de listas `repeated` sem erro em `MessageToDict`), incluir `tamanhos_repeated: dict[str, int]` em toda mensagem retornada e tornar `incluir_indice_uids` opcional (`True` apenas na raiz por padrão), atualizando `editor/mcp/ferramentas_visao_test.py`
- [x] 6.2 Implementar `editor/mcp/ferramentas_conhecimento.py` (e `editor/mcp/ferramentas_conhecimento_test.py`) expondo `aresta_obter_esquema_proto` (com suporte a filtro `tipo_mensagem`, valores de `Enum`, `oneofs` e docstrings de `proto_comments.py`), `aresta_listar_skills` e `aresta_ler_skill` (além dos recursos `aresta://esquema/proto` e `aresta://skills`), e incluir o campo `instructions` no handshake `initialize` de `editor/mcp/servidor.py`
- [x] 6.3 Atualizar os arquivos `SKILL.md` em `.agents/skills/` e a documentação `docs/mcp.md` para orientar agentes conectados a utilizarem as ferramentas MCP canônicas do editor e validar toda a suíte com 100% de cobertura nas bibliotecas modificadas e `pytest editor/arquitetura_mvc_test.py`
