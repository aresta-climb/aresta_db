# Design

## Context

O projeto `aresta_db` utiliza Python 3.13 gerenciado via `uv`, conta com MyPy estrito (`strict = true`) para validação de tipos e possui um ecossistema misto:
- Biblioteca de negócios e compilador de croquis;
- Aplicação desktop interativa em PySide6/Qt (`editor/`);
- Scripts utilitários de linha de comando (`scripts/`);
- Testes unitários com Pytest (`pytest-xdist -n 4`, `pytest-qt`).

A motivação detalhada para a introdução do Ruff encontra-se em `proposal.md`.

## Goals / Non-Goals

**Goals:**
- Configurar o Ruff de forma centralizada e declarativa na seção `[tool.ruff]` do `pyproject.toml`.
- Selecionar um conjunto equilibrado de regras voltado à prevenção de bugs, ordenação de imports (`isort`), modernização sintática para Python 3.13 (`pyupgrade`), portabilidade de caminhos (`pathlib`) e eficiência em loops (`perflint`).
- Bloquear códigos fora do padrão no script de build e testes do editor (`editor/build.py`) com diagnóstico claro e dicas de autocorreção antes de rodar o Pytest.
- Implementar verificação ultra-rápida (fail-fast) com anotações automáticas no GitHub Actions (`.github/workflows/pr-code-validator.yml`).
- Formatar e adequar o código existente do repositório utilizando `ruff check --fix` e `ruff format`.

**Non-Goals:**
- Substituir o MyPy: a verificação de integridade de tipos continua sendo responsabilidade exclusiva do MyPy.
- Impor regras pedantes de docstrings (`D`), contagem arbitrária de argumentos (`PLR0913`) ou tipagem repetitiva (`ANN`) que violem o Princípio VI do [AGENTS.md](../../AGENTS.md) (Simplicidade e Anti-Abstração).
- Integrar o Ruff como plugin bloqueante de dentro do ciclo interno do `pytest` (`pytest-ruff`), evitando desacelerar o ciclo TDD (Red-Green-Refactor).

## Decisions

### Decisão 1: Conjunto Equilibrado de Regras
- **Escolha**: Selecionar as regras `E`, `W`, `F`, `I`, `UP`, `B`, `C4`, `PTH`, `PERF`, `RUF` e `PT`.
- **Justificativa**:
  - `E`, `W`, `F`: Erros essenciais de sintaxe, imports não utilizados e variáveis indefinidas.
  - `I`: Ordenação e agrupamento automático de imports (substituindo `isort`).
  - `UP`: Modernização contínua para recursos nativos do Python 3.13.
  - `B`: Prevenção de armadilhas clássicas (como argumentos mutáveis padrão).
  - `C4`: Otimização de list/dict comprehensions.
  - `PTH`: Uso de `pathlib.Path` garantindo compatibilidade multiplataforma transparente entre Windows, Linux e macOS.
  - `PERF`: Detecção de antipadrões em loops (excluindo `PERF203`).
  - `RUF`: Proteção contra caracteres invisíveis/ambíguos e checagens modernas do Ruff.
  - `PT`: Padronização de fixtures e asserções nos testes do Pytest.
- **Alternativas consideradas**:
  - Ativar `ALL` ou incluir `ANN`, `D`, `PLR`, `COM`, `ISC`: Rejeitado. `ANN` é redundante com o MyPy; `D` gera burocracia de comentários desnecessários; `PLR` força abstrações prematuras; e `COM812`/`ISC001` conflitam diretamente com o formatador oficial (`ruff format`).

### Decisão 2: Exclusão Estrita de Arquivos de Protocol Buffers
- **Escolha**: Ignorar `*_pb2.py`, `*_pb2.pyi` e `aresta_api/proto/generated` na configuração `exclude`.
- **Justificativa**: Esses arquivos são gerados mecanicamente pelo compilador Google Protoc e não devem sofrer intervenções estilísticas ou de lint manual.

### Decisão 3: Execução Pré-Teste no Build do Editor com Streaming Direto
- **Escolha**: Na rotina `executar_testes()` de `editor/build.py`, invocar `ruff check` e `ruff format --check` antes de `pytest.main()`.
- **Justificativa**: Em caso de falha, o subprocesso imprime a saída formatada do Ruff diretamente no terminal com indicação de arquivo, linha e comando corretivo (`uv run ruff check --fix`), abortando o processo antes de gastar tempo inicializando o Qt ou rodando testes pesados.

### Decisão 4: Fail-Fast com Anotações no GitHub Actions
- **Escolha**: Adicionar steps de validação no início do workflow `pr-code-validator.yml` com `--output-format=github`.
- **Justificativa**: Permite que falhas de estilo ou imports sejam anotadas visualmente no diff do Pull Request em poucos segundos, sem necessidade de alocar runners virtuais para a suíte gráfica completa caso o código esteja em desacordo.

## Risks / Trade-offs

- **[Risco] Falsos positivos de try-except em loops**:
  - *Mitigação*: Ignorar a regra `PERF203` na configuração padrão, permitindo try-except defensivo em loops de processamento de múltiplos arquivos.
- **[Risco] Chamadas de dependências em rotas FastAPI**:
  - *Mitigação*: Ignorar a regra `B008` globalmente para compatibilidade com o padrão idiomático `Depends(...)` do FastAPI.
- **[Risco] Desvios de formatação em código legado**:
  - *Mitigação*: Executar a suite de autocorreção (`uv run ruff check --fix` e `uv run ruff format`) na submissão desta mudança, validando com a suíte de testes unitários existente para garantir zero regressão funcional.

## Migration Plan

1. Adicionar o pacote `ruff` nas dependências de desenvolvimento (`[dependency-groups.dev]`) do `pyproject.toml`.
2. Sincronizar o ambiente com `uv sync`.
3. Inserir as seções `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.lint.per-file-ignores]` e `[tool.ruff.format]` no `pyproject.toml`.
4. Executar `uv run ruff check --fix .` e `uv run ruff format .` para sanear a base existente.
5. Atualizar a função `executar_testes()` em `editor/build.py`.
6. Atualizar `.github/workflows/pr-code-validator.yml`.
7. Rodar a suíte completa de testes para certificar conformidade integral.
