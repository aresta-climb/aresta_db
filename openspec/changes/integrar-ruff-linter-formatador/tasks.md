# Tasks

## 1. Configuração e Dependências do Ruff

- [x] 1.1 Adicionar `ruff` nas dependências do grupo `dev` em `pyproject.toml` e atualizar o ambiente executando `uv sync`
- [x] 1.2 Configurar as seções `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.lint.per-file-ignores]` e `[tool.ruff.format]` em `pyproject.toml` com as regras aprovadas (`E`, `W`, `F`, `I`, `UP`, `B`, `C4`, `PTH`, `PERF`, `RUF`, `PT`), ignores e exclusões estritas de protobuf

## 2. Adequação da Base de Código Existente

- [x] 2.1 Executar `uv run ruff check --fix .` para aplicar correções automáticas de imports não utilizados, modernização sintática e boas práticas, verificando que o comando retorna código 0
- [x] 2.2 Executar `uv run ruff format .` para padronizar a formatação de todo o repositório e verificar com `uv run ruff format --check .` que não restam divergências pendentes

## 3. Integração no Script de Teste e Build do Editor

- [x] 3.1 Atualizar a rotina `executar_testes()` em `editor/build.py` para executar `ruff check` e `ruff format --check` antes de `pytest.main()`, exibindo diagnóstico visual detalhado no terminal e orientações de correção em caso de erro
- [x] 3.2 Atualizar/adicionar testes unitários em `editor/build_test.py` cobrindo o bloqueio pré-teste quando houver erro no Ruff e o fluxo normal quando a checagem for bem-sucedida

## 4. Integração no Pipeline de CI e Verificação Geral

- [x] 4.1 Adicionar steps de checagem do Ruff (`ruff check --output-format=github .` e `ruff format --check .`) no workflow `.github/workflows/pr-code-validator.yml` imediatamente antes da etapa `Run Pytest`
- [x] 4.2 Executar a suíte completa de testes (`uv run pytest`) para certificar que todas as alterações mantêm 100% de aprovação e nenhuma regressão foi introduzida
