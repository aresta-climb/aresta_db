## Context

O repositório ArestaDB gerenciava suas dependências por meio de arquivos de texto legados (`requirements.txt`, `editor/requirements.txt`, `requirements-deploy.txt`, `serving/requirements-pr_db_validator.txt` e `aresta_api/requirements.txt`). Esse formato causava dispersão de dependências, ausência de garantia determinística de versões (falta de lockfile) e lentidão no provisionamento local e em CI.

Embora uma migração anterior tenha introduzido a GitHub Action `astral-sh/setup-uv`, os pipelines continuavam utilizando a camada de compatibilidade `uv pip install` sem lockfile. A presente mudança consolida a migração completa para os padrões modernos do `uv` (PEP 621 e PEP 735).

## Goals / Non-Goals

**Goals:**
- Centralizar todas as dependências do projeto e metadados no `pyproject.toml` na raiz do repositório.
- Estruturar dependências por casos de uso através de grupos de dependências PEP 735 (`dev`, `editor`, `deploy`, `validator`).
- Gerar e versionar um arquivo de lock determinístico multiplataforma (`uv.lock`).
- Fixar a versão do interpretador Python em `3.13` via `.python-version` e `requires-python = ">=3.13, <3.14"`.
- Atualizar todos os workflows do GitHub Actions (`pr-code-validator.yml`, `pr-db-validator.yml`, `pr-integrator.yml`, `release-editor.yml`) para usar `uv sync --frozen` e atualizar o `sparse-checkout`.
- Atualizar o `GUIA_DO_DESENVOLVEDOR.md` e a documentação do projeto com as novas instruções baseadas em `uv`.
- Remover os arquivos legados `requirements*.txt`.
- Assegurar 100% de passagem nos 984+ testes unitários e de integração existentes via `uv run pytest`.

**Non-Goals:**
- Não transformar o repositório em um ecossistema complexo de múltiplos pacotes em workspace (`uv workspace`); a estrutura monorepo com grupos de dependência atende perfeitamente a todas as necessidades atuais.
- Não alterar as bibliotecas ou versões mínimas em uso além do necessário para a compatibilidade e resolução com `uv`.

## Conformidade com os Princípios de Engenharia (PRINCIPIOS.md)

- **I. Tudo em Português**: Toda a documentação, metadados do projeto (descrição do `pyproject.toml`), nomes de seções e comentários são redigidos obrigatoriamente em português brasileiro.
- **II. Library-First & VI. Simplicidade e Anti-Abstração**: O `pyproject.toml` adota uma abordagem puramente declarativa direta utilizando padrões oficiais da comunidade Python (PEP 621 e PEP 735), evitando abstrações prematuras, metapacotes ou plugins desnecessários.
- **III. 100% Unit Test Coverage & IV. Imperativo do TDD**: A migração de dependências exige que o conjunto integral de testes unitários e de integração (984+ testes) seja executado e passe integralmente (`uv run pytest`) antes de qualquer remoção de arquivos legados.
- **V. Testes de Integração em Primeiro Lugar**: O fluxo fim-a-fim de instalação e resolução (`uv sync`), bem como o empacotamento do editor e as rotinas de deploy, são validados antes da consolidação dos arquivos.

## Decisions

### 1. Centralização com PEP 735 (`[dependency-groups]`) vs Subprojetos Múltiplos
- **Decisão**: Utilizar um único arquivo `pyproject.toml` na raiz com grupos de dependências declarativos (`[dependency-groups]`).
- **Alternativas consideradas**: Criar subprojetos isolados com `pyproject.toml` em cada subpasta (`editor/`, `serving/`, etc.).
- **Justificativa**: O ArestaDB opera como uma base de dados e conjunto de ferramentas integradas (scripts, editor PyQt6, validador de banco). Um `pyproject.toml` central simplifica a manutenção, evita versionamentos redundantes e permite instalações seletivas (ex: `uv sync --group editor` ou `uv sync --all-groups`).

### 2. Marcadores de Ambiente para Dependências Windows (`winrt-*`)
- **Decisão**: Usar marcadores PEP 508 diretamente no `pyproject.toml` (`winrt-Windows.Services.Store; sys_platform == 'win32'`).
- **Justificativa**: O `uv` resolve árvores de dependência universais, permitindo gerar um `uv.lock` único e consistente que funciona perfeitamente tanto no Ubuntu (CI) quanto no Windows (ambiente dos desenvolvedores e lançamento do editor).

### 3. Restrição Estrita do Python 3.13
- **Decisão**: Configurar `requires-python = ">=3.13, <3.14"` no `pyproject.toml` e adicionar `.python-version` com `3.13`.
- **Justificativa**: O ecossistema PaddlePaddle / PaddleOCR não possui suporte estável a Python 3.14 no momento. Garantir a versão 3.13 no nível do `uv` evita erros de compilação ou resolução em máquinas de novos colaboradores.

### 4. CI Determinístico com `uv sync --frozen`
- **Decisão**: Substituir passos de `uv pip install` nos workflows do GitHub Actions por `uv sync --frozen` (com grupos apropriados) e `uv run`.
- **Justificativa**: `uv sync --frozen` não consulta a internet para resolver versões, garantindo que o CI execute exatamente as versões validadas no `uv.lock`, com tempo de setup de dependências reduzido para poucos segundos.

### 5. Atualização de Sparse-Checkout no CI
- **Decisão**: Incluir explicitamente `pyproject.toml` e `uv.lock` nos blocos de `sparse-checkout` dos workflows do GitHub Actions.
- **Justificativa**: Workflows que utilizam checkout parcial precisam ter acesso ao arquivo de projeto e de lock para que o `setup-uv` e o `uv sync` consigam inicializar o ambiente virtual.

## Risks / Trade-offs

- **[Risco: Workflows de CI falharem por falta do `pyproject.toml` no sparse-checkout]** → **Mitigação**: Revisar e atualizar todas as diretivas `sparse-checkout` em `.github/workflows/*.yml`.
- **[Risco: Scripts externos ou desenvolvedores habituados ao pip tentarem rodar `pip install`]** → **Mitigação**: Atualizar detalhadamente o `GUIA_DO_DESENVOLVEDOR.md` e o `README.md`, indicando o fluxo com `uv sync` e `uv run`.
- **[Risco: Conflito de dependências durante a resolução inicial do lockfile]** → **Mitigação**: Testar a resolução e executar toda a suíte de testes (984 testes) via `uv run pytest` antes de finalizar a implementação.
