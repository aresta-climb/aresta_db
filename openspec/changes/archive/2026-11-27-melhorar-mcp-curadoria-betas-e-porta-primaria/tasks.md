# Tasks

## 1. Resolução da Porta Primária MCP em Múltiplas Janelas

- [x] 1.1 (TDD) Adicionar `obter_porta_primaria_ativa` em `editor/mcp/sessao.py` (com testes em `editor/mcp/sessao_test.py`) priorizando `mcp_sessao.json` e usando `porta_fallback`/`PORTA_MCP_PADRAO` como fallback, verificando aprovação em `uv run pytest editor/mcp/sessao_test.py`.
- [x] 1.2 (TDD) Atualizar `DialogoConexaoMcp` (`editor/views/dialogos/dialogo_conexao_mcp.py`), `JanelaPrincipal._exibir_conexao_mcp` (`editor/legacy_views/area_principal.py`) e `TelaDeCarregamento.ao_clicar_conectar_mcp` (`editor/legacy_views/tela_de_carregamento.py`) para resolver e exibir a porta primária ativa (com testes de integração multi-janela sem mocks em `editor/views/dialogos/dialogo_conexao_mcp_test.py`, `editor/legacy_views/area_principal_test.py` e `editor/legacy_views/tela_de_carregamento_test.py`), verificando aprovação via `pytest`.

## 2. Prompt e Banner MCP Contextuais na Aba Betas

- [x] 2.1 (TDD) Implementar `gerar_prompt_mcp_avaliacao_betas` e `gerar_instrucoes_banner_mcp_avaliacao` em `coleta_de_betas/curadoria/painel_curadoria.py` e atualizar `atualizar_visualizacao()` / `_copiar_prompt_mcp()` para gerar dinamicamente o texto citando o servidor `editor-aresta`, `aresta_ler_skill(nome_skill="avaliar_betas_croqui")` e `id_croqui` para avaliar todo o croqui ativo (independentemente do filtro de escalada no combo), verificando em `uv run pytest coleta_de_betas/curadoria/painel_curadoria_test.py`.

## 3. Adição para Revisão e Remoção de Betas por URL via MCP

- [x] 3.1 (TDD) Implementar `adicionar_betas_para_revisao` e `remover_betas_por_url` em `editor/controllers/croqui_controller.py` (com normalização de URL, inferência de `FonteMidia`, resgate incondicional de `betas_rejeitados`, validação fail-fast e atomicidade com `Undo/Redo`), verificando em `uv run pytest editor/controllers/croqui_controller_test.py`.
- [x] 3.2 (TDD) Registrar e testar as ferramentas `aresta_adicionar_betas_revisao` e `aresta_remover_betas` em `editor/mcp/ferramentas_betas.py`, `editor/mcp/ferramentas_betas_test.py` e `editor/mcp/registro_ferramentas_test.py` (incluindo roteamento multi-janela com `id_croqui` e erros fail-fast `isError: True`), verificando em `uv run pytest editor/mcp/ferramentas_betas_test.py editor/mcp/registro_ferramentas_test.py`.

## 4. Skills de Domínio e Verificação Integral

- [x] 4.1 Atualizar `.agents/skills/avaliar_betas_croqui/SKILL.md`, `.agents/skills/coletar_betas_croqui/SKILL.md` e `.agents/skills/resolver_feedback_croqui/SKILL.md` com o servidor `editor-aresta`, propagação de `id_croqui`, alternativa para clientes MCP sem `define_subagent` e governança explícita de `aresta_adicionar_betas_revisao` / `aresta_remover_betas`.
- [x] 4.2 Executar a suíte completa dos módulos alterados com cobertura de 100%, `uv run ruff check .`, `uv run ruff format --check .` e `uv run mypy .` garantindo zero erros ou linhas descobertas.

## Workflow follow-up

- Sincronizar os delta specs para `openspec/specs/`, validar `openspec validate --specs` e arquivar a mudança em `openspec/changes/archive/2026-11-27-melhorar-mcp-curadoria-betas-e-porta-primaria`.
- Realizar commit com assinatura DCO (`git commit -s`) e `git push`.
