# Tasks

## 1. Dependências e Deduplicação da GitHub Action

- [ ] 1.1 Criar o grupo `editor_headless` em `pyproject.toml`, configurar `editor` com `{ include-group = "editor_headless" }` sem duplicar pacotes, atualizar `uv.lock` e verificar que `uv lock --check` passa sem erros
- [ ] 1.2 Atualizar `.github/workflows/ai-feedback-solver.yml` para deduplicar disparos de Issue (`issues: types: [labeled]` com filtro `feedback:croqui`), adicionar `concurrency` por número do alvo e sincronizar `--only-group editor_headless` com `QT_QPA_PLATFORM=offscreen`, verificando a sintaxe YAML do workflow

## 2. Modo Headless Oficial do Editor e Registro MCP Unificado

- [ ] 2.1 Implementar via TDD `HeadlessWorkspace` em `editor/core/workspace.py` (compilando em `TemporaryDirectory` isolado sem tocar em `generated/` ou `STATUS_CROQUIS.md`) com espelhamento em `editor/core/workspace_test.py` e verificar 100% de cobertura comportamental
- [ ] 2.2 Extrair o registro canônico unificado de ferramentas MCP para `editor/mcp/registro_ferramentas.py` (`editor/mcp/registro_ferramentas_test.py`) e reutilizá-lo em `editor/legacy_views/area_principal.py`, verificando que os testes de `area_principal_test.py` e `registro_ferramentas_test.py` passam com 100% de cobertura
- [ ] 2.3 Implementar via TDD `SessaoEditorHeadless` e loop `stdio` em `editor/mcp/sessao_headless.py` (`editor/mcp/sessao_headless_test.py`) e integrar a flag `--headless` em `editor/main.py` (`editor/main_test.py`), atualizando `docs/mcp.md` e verificando execução real sobre um croqui temporário sem `QWidget`

## 3. Skill de Domínio, Warm-Start e Guarda de Mudança Maior

- [ ] 3.1 Criar a skill `.agents/skills/resolver_feedback_croqui/SKILL.md` com instruções concisas de resolução via Editor MCP (endereçamento por `UID`, `aresta_migrar_escalada`, criação de setor, `aresta_renderizar_mapa` sob demanda e critérios de `nao_acionavel`) e verificar sua listagem por `aresta_listar_skills`
- [ ] 3.2 Atualizar `serving/agente_feedback/localizador_arquivos_croqui.py` (`localizador_arquivos_croqui_test.py`) para extrair contexto da Issue/`/ai-fix` e gerar o pacote *Warm-Start* estrutural a partir da `SessaoEditorHeadless` (índice completo de `UID`s + subárvore foco), removendo o módulo legado `renderizador_regua_mapa.py` (`renderizador_regua_mapa_test.py`) e verificando 100% de cobertura
- [ ] 3.3 Implementar via TDD o avaliador determinístico de impacto `serving/agente_feedback/avaliador_impacto_feedback.py` (`avaliador_impacto_feedback_test.py`) sobre `diff_croqui_pr_lib` (detectando exclusões líquidas, `>1` setor adicionado, `>5` escaladas alteradas/adicionadas e mudança de `id`/`publicar_croqui`) e verificar 100% de cobertura

## 4. Cliente Gemini Function Calling, Orquestrador Headless e CLI

- [ ] 4.1 Refatorar via TDD `serving/agente_feedback/cliente_gemini_feedback.py` e `cliente_gemini_feedback_fake.py` (com `cliente_gemini_feedback_test.py` e `cliente_gemini_feedback_fake_test.py`) para suportar turnos de *Function Calling* (incluindo schemas MCP adaptados, `finalizar_resolucao` em paralelo no 1º turno e respostas multimodais de `aresta_renderizar_mapa`), verificando 100% de cobertura
- [ ] 4.2 Refatorar via TDD `serving/agente_feedback/orquestrador_resolucao_feedback.py` (`orquestrador_resolucao_feedback_test.py`) e `serving/resolver_feedback_ia.py` (`resolver_feedback_ia_test.py`) integrando `SessaoEditorHeadless`, resolução em 1 turno, cenário multi-turno da Issue #108 (criação de setor + `aresta_migrar_escalada` + commit com `git add -A`), *Circuit Breaker*, desistência voluntária, guarda de Mudança Maior e Hard Jail com rollback completo, atualizando `docs/guia_configuracao_ai_studio_feedback.md` e verificando 100% de cobertura

## 5. Verificação Integrada de Qualidade

- [ ] 5.1 Executar `uv run ruff check .`, `uv run mypy .` e a suíte completa `uv run pytest` (incluindo regressões do Robô Caótico), garantindo zero erros de lint, tipagem estática e 100% de aprovação nos testes
