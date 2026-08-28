## Why

Atualmente, o repositório gerencia dependências Python de forma fragmentada através de múltiplos arquivos `requirements*.txt` dispersos (`requirements.txt`, `editor/requirements.txt`, `requirements-deploy.txt`, `serving/requirements-pr_db_validator.txt`, `aresta_api/requirements.txt`), sem um arquivo de lock determinístico (`uv.lock`) e instruindo o uso manual do `pip` na documentação. 

Embora o CI já utilize o `setup-uv`, ele ainda roda comandos imperativos de `uv pip install`. A transição completa para o ecossistema nativo do `uv` (com `pyproject.toml`, PEP 735 Dependency Groups e `uv.lock`) padroniza o ambiente de desenvolvimento, garante builds 100% determinísticos e reproduzíveis entre Linux e Windows, e reduz o tempo de instalação local e no CI para frações de segundo.

## What Changes

- **Criação do `pyproject.toml`**: Centralização de metadados do projeto, restrição do interpretador Python (`>=3.13, <3.14`) e unificação de todas as dependências em grupos (`dev`, `editor`, `deploy`, `validator`).
- **Geração e versionamento do `uv.lock`**: Lockfile universal e determinístico para todas as plataformas (Linux e Windows), eliminando riscos de desvio ou quebras com versões upstream.
- **Fixação da versão do Python**: Inclusão de arquivo `.python-version` apontando para `3.13`.
- **Modernização do CI/CD**: Atualização dos workflows do GitHub Actions (`pr-code-validator.yml`, `pr-db-validator.yml`, `pr-integrator.yml`, `release-editor.yml`) para utilizarem `uv sync --frozen` / `uv run` e cache baseado em `uv.lock` e `pyproject.toml`.
- **Atualização do Guia do Desenvolvedor e Documentação**: Substituição de instruções legadas do `pip` por comandos do `uv` (`uv sync`, `uv run`).
- **Eliminação dos arquivos `requirements*.txt` legados**: Remoção dos arquivos de requirements dispersos em favor da declaração centralizada no `pyproject.toml`.

## Capabilities

### New Capabilities
- `gerenciamento-dependencias-uv`: Gerenciamento declarativo e determinístico de dependências do projeto através de `pyproject.toml`, grupos de dependência (PEP 735), lockfile multiplataforma `uv.lock` e execução padronizada com `uv run`.

### Modified Capabilities
- `otimizacao-ci-uv`: Atualização dos requisitos de instalação e execução em CI para utilizar sincronização determinística via `uv sync` com `uv.lock` em vez de `uv pip install`.

## Impact

- **Ambiente de Desenvolvimento**: Desenvolvedores e agentes utilizarão `uv sync` e `uv run` para testar e executar ferramentas.
- **CI/CD**: Workflows de CI/CD terão tempo de setup reduzido, cache baseado em `uv.lock`, e listas de `sparse-checkout` atualizadas para incluir `pyproject.toml` e `uv.lock`.
- **Compatibilidade Multi-plataforma**: Dependências exclusivas do Windows (como `winrt-*` do editor) são isoladas via marcadores de ambiente (`markers = "sys_platform == 'win32'"`) mantendo integridade no Linux e Windows.
