# Tasks

## 1. Infraestrutura e Despacho Thread-Safe

- [ ] 1.1 Configurar a dependência do pacote `mcp` no grupo `editor` do `pyproject.toml` e verificar a sincronização do ambiente de desenvolvimento
- [ ] 1.2 Implementar a classe `DespachanteQt` em `editor/mcp/despachante.py` com testes em `editor/mcp/despachante_test.py` cobrindo despacho para thread principal, tratamento de exceções e timeouts
- [ ] 1.3 Implementar o gerenciador de sessão local efêmera em `editor/mcp/sessao.py` com testes em `editor/mcp/sessao_test.py` verificando gravação atômica da porta e token em `mcp_sessao.json`

## 2. Servidor MCP e Transporte Híbrido

- [ ] 2.1 Implementar o servidor SSE HTTP local em `editor/mcp/servidor.py` utilizando FastAPI com testes em `editor/mcp/servidor_test.py` validando o endpoint `/mcp/sse` e autenticação por token de sessão
- [ ] 2.2 Implementar a ponte CLI `editor/mcp/bridge.py` operando via `stdio` com testes em `editor/mcp/bridge_test.py` verificando o encaminhamento bidirecional de JSON-RPC para o servidor SSE local

## 3. Catálogo de Ferramentas de Mutação 1:1 (Comandos do Histórico)

- [ ] 3.1 Implementar a ferramenta `aresta_alterar_primitivo` em `editor/mcp/ferramentas_comandos.py` com testes em `editor/mcp/ferramentas_comandos_test.py` validando resolução de caminho e criação do `CmdAlterarPrimitivo`
- [ ] 3.2 Implementar as ferramentas `aresta_adicionar_repeated`, `aresta_remover_repeated` e `aresta_mover_repeated` com testes cobrindo inserção, remoção e reordenação de itens com reversão via `QUndoStack`
- [ ] 3.3 Implementar as ferramentas `aresta_alterar_oneof` e `aresta_renomear_escalada` com testes validando a sincronização automática de referências entre vias, mapas e imagens
- [ ] 3.4 Implementar as ferramentas de controle transacional `aresta_iniciar_macro` e `aresta_finalizar_macro` com testes comprovando o agrupamento atômico de múltiplos comandos no `CmdMacro`

## 4. Ferramentas de Visão Multimodal e Inspeção Estrutural

- [ ] 4.1 Implementar a ferramenta `aresta_capturar_canvas` em `editor/mcp/ferramentas_visao.py` com testes em `editor/mcp/ferramentas_visao_test.py` verificando a extração do viewport gráfico e retorno em Base64 PNG
- [ ] 4.2 Implementar os recursos e ferramentas de leitura estrutural `aresta_obter_arvore` e `aresta_obter_selecao_atual` com testes verificando a serialização correta da árvore do croqui e dos caminhos de entidade

## 5. Ferramentas de Ciclo de Vida e Interface

- [ ] 5.1 Implementar as ferramentas de compilação e histórico `aresta_compilar`, `aresta_salvar`, `aresta_desfazer` e `aresta_refazer` em `editor/mcp/ferramentas_ciclo_vida.py` com testes em `editor/mcp/ferramentas_ciclo_vida_test.py`
- [ ] 5.2 Implementar a ferramenta `aresta_focar_elemento` com testes verificando a atualização da navegação visual da árvore e dos seletores da interface

## 6. Integração Global e Documentação

- [ ] 6.1 Integrar o ciclo de vida do `ServidorMCP` ao arranque e fechamento da `JanelaPrincipal` em `editor/legacy_views/area_principal.py` com testes em `editor/legacy_views/area_principal_test.py`
- [ ] 6.2 Criar suíte de testes de integração ponta a ponta em `editor/mcp/mcp_e2e_test.py` simulando um agente criando setores, inserindo vias, capturando canvas e compilando o croqui
- [ ] 6.3 Criar o guia de uso e configuração do MCP em `docs/mcp.md` com instruções detalhadas para Claude Desktop, Cursor e Antigravity
