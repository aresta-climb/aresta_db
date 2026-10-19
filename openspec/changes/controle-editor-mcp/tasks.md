# Tasks

## 1. Infraestrutura, Despacho Thread-Safe e Resolução por UID

- [ ] 1.1 Adicionar suporte a `iniciar_grupo_undo`, `finalizar_grupo_undo` (`CmdMacro`) e `alterar_multiplos_repeated_items` (`CmdAlterarMultiplosRepeatedItems`) em `editor/controllers/croqui_controller.py` com testes em `editor/controllers/croqui_controller_test.py`
- [ ] 1.2 Implementar a classe `DespachanteQt` em `editor/mcp/despachante.py` com testes comportamentais em `editor/mcp/despachante_test.py` cobrindo execução na thread principal, propagação de exceções e timeouts
- [ ] 1.3 Implementar o gerenciador de sessão local multiplataforma em `editor/mcp/sessao.py` (porta padrão `27378`, fallback automático e persistência em `obter_diretorio_base_app() / "mcp_sessao.json"`) com testes em `editor/mcp/sessao_test.py`
- [ ] 1.4 Implementar o resolvedor de alvos híbrido (`resolver_alvo_mcp` por `UID` do `IndiceUidsModel`, `<uid>.<subcaminho>` e caminho posicional) em `editor/mcp/resolvedor_alvo.py` com testes comportamentais reais em `editor/mcp/resolvedor_alvo_test.py`

## 2. Servidor MCP JSON-RPC/SSE e Transporte Híbrido

- [ ] 2.1 Implementar o servidor JSON-RPC 2.0 sobre HTTP/SSE local em `editor/mcp/servidor.py` utilizando FastAPI vinculado a `127.0.0.1:27378` (com fallback de porta livre e suporte a `POST /mcp`, `GET /mcp/sse` e `POST /mcp/messages`) e testes em `editor/mcp/servidor_test.py`
- [ ] 2.2 Implementar a ponte CLI `editor/mcp/bridge.py` operando via `stdio` com testes em `editor/mcp/bridge_test.py` verificando a descoberta via `mcp_sessao.json` e o encaminhamento bidirecional de mensagens JSON-RPC

## 3. Catálogo de Ferramentas de Mutação 1:1 (via Controllers)

- [ ] 3.1 Implementar `aresta_alterar_primitivo` e `aresta_alterar_oneof` em `editor/mcp/ferramentas_comandos.py` despachando via `CroquiController` com testes reais (sem mocks internos) em `editor/mcp/ferramentas_comandos_test.py` validando mutação por `UID` e caminho com `undo/redo`
- [ ] 3.2 Implementar `aresta_adicionar_repeated`, `aresta_remover_repeated`, `aresta_mover_repeated`, `aresta_alterar_item_repeated` e `aresta_alterar_multiplos_repeated` garantindo geração e retorno imediato de `uid` NanoID com testes comportamentais
- [ ] 3.3 Implementar `aresta_renomear_escalada`, `aresta_migrar_setor`, `aresta_alterar_campo_imagem`, `aresta_inserir_imagem_markdown`, `aresta_inserir_botao_markdown` e ferramentas topológicas de mapas (`aresta_adicionar_mapa_arquivo`, adição de POIs e referências por `alvo_uid` via `MapasController`) com testes cobrindo sincronização de referências
- [ ] 3.4 Implementar as ferramentas transacionais `aresta_iniciar_macro` e `aresta_finalizar_macro` com testes comprovando o agrupamento atômico de múltiplos comandos em um único `CmdMacro` e validar conformidade com `pytest editor/arquitetura_mvc_test.py`

## 4. Ferramentas de Visão Multimodal e Inspeção Estrutural

- [ ] 4.1 Implementar a ferramenta `aresta_capturar_canvas` em `editor/mcp/ferramentas_visao.py` com testes em `editor/mcp/ferramentas_visao_test.py` verificando a captura de imagem PNG Base64 dos viewports de mapa, foto e dados
- [ ] 4.2 Implementar as ferramentas de leitura estrutural `aresta_obter_arvore` e `aresta_obter_selecao_atual` retornando a árvore do croqui enriquecida com `uid`s, caminhos formatados (`Grupo > Setor > Escalada`) e seleção ativa da UI com testes unitários

## 5. Ferramentas de Ciclo de Vida, Workspace e Diálogo de Conexão

- [ ] 5.1 Implementar as ferramentas `aresta_compilar`, `aresta_salvar`, `aresta_desfazer`, `aresta_refazer`, `aresta_focar_elemento` e `aresta_status_workspace` em `editor/mcp/ferramentas_ciclo_vida.py` (reutilizando o pipeline de salvamento/compilação em RAM) com testes em `editor/mcp/ferramentas_ciclo_vida_test.py`
- [ ] 5.2 Implementar o diálogo `DialogoConexaoMcp` em `editor/views/dialogos/dialogo_conexao_mcp.py` com testes em `editor/views/dialogos/dialogo_conexao_mcp_test.py` verificando a exibição da porta ativa e a cópia dos snippets para Antigravity, Codex, Claude Desktop e Cursor

## 6. Integração Global e Documentação

- [ ] 6.1 Integrar o arranque/encerramento do `ServidorMCP` e a ação de menu `Conectar Agente de IA (MCP)...` na `JanelaPrincipal` em `editor/legacy_views/area_principal.py` e validar nos testes de `editor/legacy_views/area_principal_test.py`
- [ ] 6.2 Criar o guia de uso e conexão em `docs/mcp.md` detalhando o funcionamento com Google Antigravity, OpenAI Codex, Claude Desktop e Cursor
