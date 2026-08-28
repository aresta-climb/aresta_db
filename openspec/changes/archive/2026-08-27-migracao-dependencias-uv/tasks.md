## 1. Configuração do Projeto e Lockfile

- [x] 1.1 Criar o arquivo `.python-version` fixando a versão `3.13`.
- [x] 1.2 Criar o arquivo `pyproject.toml` na raiz em português brasileiro com metadados do projeto, dependências base e grupos de dependências PEP 735 (`dev`, `editor`, `deploy`, `validator`).
- [x] 1.3 Gerar o lockfile determinístico multiplataforma `uv.lock` através do comando `uv lock`.
- [x] 1.4 Testar sincronização local via `uv sync --all-groups` e validar execução completa dos testes de integração e unitários com `uv run pytest` assegurando 100% de aprovação.

## 2. Atualização dos Workflows do GitHub Actions

- [x] 2.1 Atualizar `.github/workflows/pr-code-validator.yml` incluindo `pyproject.toml` e `uv.lock` no sparse-checkout, configurando cache para `uv.lock` e executando `uv sync --frozen --group dev --group editor` e `uv run pytest`.
- [x] 2.2 Atualizar `.github/workflows/pr-db-validator.yml` incluindo `pyproject.toml` e `uv.lock` no sparse-checkout, configurando cache para `uv.lock` e executando `uv sync --frozen --only-group validator` e `uv run`.
- [x] 2.3 Atualizar `.github/workflows/pr-integrator.yml` incluindo `pyproject.toml` e `uv.lock` no sparse-checkout, configurando cache para `uv.lock` e executando `uv sync --frozen --only-group deploy` e `uv run`.
- [x] 2.4 Atualizar `.github/workflows/release-editor.yml` incluindo `pyproject.toml` e `uv.lock` no sparse-checkout, configurando cache para `uv.lock` e executando `uv sync --frozen --all-groups` e `uv run`.

## 3. Limpeza de Arquivos Legados e Validação Final

- [x] 3.1 Remover arquivos legados `requirements.txt`, `editor/requirements.txt`, `requirements-deploy.txt`, `serving/requirements-pr_db_validator.txt` e `aresta_api/requirements.txt`.
- [x] 3.2 Atualizar o `GUIA_DO_DESENVOLVEDOR.md` em português brasileiro substituindo comandos do `pip` por instruções baseadas em `uv` (`uv sync`, `uv run`).
- [x] 3.3 Atualizar referências legadas ao `pip` em comentários de scripts (`scripts/repartir_pdf.py`) e na documentação relevante.
- [x] 3.4 Executar validação final da suíte de testes com `uv run pytest` comprovando 100% de testes unitários e de integração verdes sem arquivos `requirements*.txt`.
