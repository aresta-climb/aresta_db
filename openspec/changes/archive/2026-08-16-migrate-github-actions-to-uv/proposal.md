## Why

A instalação de dependências Python nos fluxos do GitHub Actions consome atualmente cerca de 3 minutos por execução utilizando o `pip` padrão e `actions/setup-python`. O gerenciador `uv` (`setup-uv`) já possui suporte nativo para instalar versões do Python e gerenciar o cache de pacotes, tornando o `actions/setup-python` completamente desnecessário e simplificando a infraestrutura de CI.

## What Changes

- Substituição completa do `actions/setup-python` pelo `astral-sh/setup-uv@v10`.
- Configuração do parâmetro `python-version: '3.13'` e `enable-cache: true` diretamente no `setup-uv`.
- Substituição dos comandos de instalação `pip install` por `uv pip install --system`.
- Simplificação dos steps nos workflows, reduzindo o número de actions e acelerando o pipeline para poucos segundos.

## Capabilities

### New Capabilities
- `otimizacao-ci-uv`: Instalação do Python e aceleração dos ambientes de CI do GitHub Actions via gerenciador `uv` unificado com cache inteligente.

### Modified Capabilities

## Impact

Workflows afetados em `.github/workflows/`:
- `.github/workflows/pr-db-validator.yml`
- `.github/workflows/pr-code-validator.yml`
- `.github/workflows/pr-integrator.yml`
- `.github/workflows/release-editor.yml`

Remove uma action externa redundante (`actions/setup-python`), mantendo 100% de compatibilidade e velocidade máxima.
