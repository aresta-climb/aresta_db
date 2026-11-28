# Tasks

## 1. Biblioteca de Trava por Seleção e por Croqui

- [x] 1.1 Refatorar `editor/core/instancia_unica.py` e `editor/core/instancia_unica_test.py` via TDD (removendo `NOME_SERVIDOR_PADRAO`, adicionando `NOME_SERVIDOR_SELECAO`, `ARESTA_PREFIXO_IPC`, `obter_nome_servidor_selecao`, `verificar_selecao_ja_aberta`, `iniciar_trava_selecao`, `encerrar_servidor_local` e `extrair_id_croqui_de_pasta`, exigindo `nome_servidor` obrigatório e `ValueError` em ID vazio) e verificar 100% de cobertura com `uv run pytest -n 0 editor/core/instancia_unica_test.py --cov=editor.core.instancia_unica --cov-report=term-missing`

## 2. Proteção de Concorrência Multi-Processo

- [x] 2.1 Atualizar `editor/mcp/sessao.py`, `editor/core/sync.py` e `editor/core/workspace.py` (com seus respectivos `_test.py` via TDD) para garantir gravação atômica preservando a sessão primária em `mcp_sessao.json`, lock externo nas operações Git de `GerenciadorSincronizacao` e lock fora do repo nas compilações de `LocalRepoWorkspace`, verificando 100% de cobertura com `uv run pytest -n 0 editor/mcp/sessao_test.py editor/core/sync_test.py editor/core/workspace_test.py --cov=editor.mcp.sessao --cov=editor.core.sync --cov=editor.core.workspace --cov-report=term-missing`

## 3. Ciclo de Vida da Trava nas Janelas de Seleção e Edição

- [x] 3.1 Adicionar guarda de croqui já aberto em `editor/legacy_views/tela_de_carregamento.py` (novo, oficial e histórico) e ciclo completo de trava por croqui em `editor/legacy_views/area_principal.py` (aquisição, atualização ao renomear ID e liberação no encerramento), com testes comportamentais reais em `tela_de_carregamento_test.py` (100% de cobertura) e `area_principal_test.py`

## 4. Ponto de Entrada `editor/main.py` e Suíte Sem Mocks

- [x] 4.1 Atualizar `editor/main.py` (`ControladorAplicativo` e `main()`) para resolver o croqui antes da verificação de instância, usar `iniciar_trava_croqui` / `iniciar_trava_selecao` e liberar `app.servidor_local` na transição para `JanelaPrincipal`, refatorando e expandindo `editor/main_test.py` sem mocks internos e validando 100% de cobertura em `editor/main.py`

## 5. Verificação Integral de Qualidade

- [x] 5.1 Executar `ruff check`, `ruff format --check`, `mypy` e `pytest --cov` em todos os módulos e testes afetados confirmando 100% de cobertura nos módulos alvo e aprovação integral dos testes relacionados

## Workflow follow-up

- Sincronizar as delta specs para as especificações principais em `openspec/specs/` e validar com `openspec validate --specs`.
- Arquivar a change em `openspec/changes/archive/2026-11-27-trava-instancia-por-croqui`, fazer commit assinado (`-s`) apenas dos arquivos desta tarefa e enviar via `git push`.
