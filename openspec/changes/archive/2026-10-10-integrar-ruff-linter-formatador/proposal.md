# Proposal

## Why

O repositório `aresta_db` conta com contribuições simultâneas de desenvolvedores humanos e múltiplos agentes autônomos de IA (Antigravity, OPSX), tornando essencial a garantia de consistência de código, remoção de imports ou variáveis mortas e aderência às melhores práticas do Python 3.13 e dos princípios de engenharia do repositório ([AGENTS.md](../../AGENTS.md)). Integrar o Ruff como linter e formatador unificado de alta performance (Rust) permite validações instantâneas (< 100ms), prevenção de bugs e formatação consistente sem degradar a velocidade do ciclo de TDD.

## What Changes

- Adição do `ruff` como dependência de desenvolvimento no grupo `dev` do `pyproject.toml`.
- Configuração declarativa da seção `[tool.ruff]` no `pyproject.toml` com um conjunto de regras equilibrado:
  - Seleção das regras: `E`, `W` (pycodestyle), `F` (Pyflakes), `I` (isort), `UP` (pyupgrade Python 3.13), `B` (flake8-bugbear), `C4` (flake8-comprehensions), `PTH` (flake8-use-pathlib), `PERF` (perflint), `RUF` (regras nativas do Ruff) e `PT` (flake8-pytest-style).
  - Ignorados explicitamente: `E501` (comprimento de linha delegado ao formatador), `B008` (chamadas em argumentos padrão para dependências do FastAPI) e `PERF203` (try-except dentro de loops em processamento em lote).
  - Exclusão estrita de artefatos gerados do Protobuf (`*_pb2.py`, `*_pb2.pyi`, `aresta_api/proto/generated/`) e diretórios temporários/build.
  - Regras relaxadas para arquivos de teste (`tests/*`, `*_test.py`).
- Integração da checagem do Ruff no script de testes e empacotamento do editor (`editor/build.py`): execução sequencial de `ruff check` e `ruff format --check` com saída visual detalhada e orientações de autocorreção (`--fix`) antes do `pytest`.
- Integração de validação rápida no pipeline de CI do GitHub Actions (`.github/workflows/pr-code-validator.yml`): execução de `ruff check --output-format=github` e `ruff format --check` antes da suíte pesada de testes no Xvfb.

## Capabilities

### New Capabilities
- `padronizacao-qualidade-codigo-ruff`: Define os requisitos de análise estática, ordenação de imports, modernização sintática e conformidade de formatação com Ruff para todo o código Python do repositório, com integração no CI e nos utilitários de build.

### Modified Capabilities
<!-- Nenhuma capability existente tem seus requisitos alterados. -->

## Impact

- **Dependências**: Adição de `ruff` no grupo `dev` em `pyproject.toml` e atualização do `uv.lock`.
- **Scripts de Build**: `editor/build.py` passa a invocar `ruff check` e `ruff format --check` na rotina `executar_testes()`.
- **Integração Contínua**: `.github/workflows/pr-code-validator.yml` passa a conter um passo de fail-fast de lint e formatação.
- **Base de Código**: Correção de eventuais imports não utilizados, formatação padronizada e modernização de caminhos com `pathlib` conforme detectado pelo linter.
