## 1. Atualizar Workflows de Validação de Pull Request

- [x] 1.1 Atualizar `.github/workflows/pr-db-validator.yml` substituindo `actions/setup-python` por `astral-sh/setup-uv@v10` com `python-version: "3.13"` e `enable-cache: true`, e instalando via `uv pip install --system`.
- [x] 1.2 Atualizar `.github/workflows/pr-code-validator.yml` substituindo `actions/setup-python` por `astral-sh/setup-uv@v10` com `python-version: "3.13"` e `enable-cache: true`, e instalando via `uv pip install --system`.
- [x] 1.3 Atualizar `.github/workflows/pr-integrator.yml` substituindo `actions/setup-python` por `astral-sh/setup-uv@v10` com `python-version: "3.13"` e `enable-cache: true`, e instalando via `uv pip install --system`.

## 2. Atualizar Workflows de Lançamento e Validação Final

- [x] 2.1 Atualizar `.github/workflows/release-editor.yml` substituindo `actions/setup-python` por `astral-sh/setup-uv@v10` com `python-version: "3.13"` e `enable-cache: true`, e instalando via `uv pip install --system`.
- [x] 2.2 Verificar a sintaxe dos arquivos YAML modificados garantindo que não há regressões estruturais.
