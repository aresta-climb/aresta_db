## Context

Atualmente, os workflows de validação de Pull Requests (`pr-db-validator.yml`, `pr-code-validator.yml`, `pr-integrator.yml`) e de lançamento (`release-editor.yml`) utilizavam a action `actions/setup-python` combinada com comandos `pip install`. O `setup-uv` (versão 10+) provê provisionamento nativo de versões de Python via parâmetro `python-version` e cache granular via `cache-dependency-glob`, tornando a action `actions/setup-python` obsoleta em nosso pipeline.

Seguindo o princípio de simplicidade e anti-abstração (`PRINCIPIOS.md`), consolidamos todo o setup de Python e gerenciamento de dependências no `astral-sh/setup-uv@v10`.

## Goals / Non-Goals

**Goals:**
- Consolidar a instalação do interpretador Python e o gerenciamento de pacotes em um único step (`astral-sh/setup-uv@v10`).
- Configurar explicitamente `cache-dependency-glob` para mapear dependências diretas e aninhadas (como `requirements-deploy.txt` em `pr-db-validator.yml`).
- Reduzir o tempo de setup e instalação para poucos segundos nos runners Ubuntu e Windows.
- Manter compatibilidade total com os arquivos de dependência existentes (`requirements.txt`, `editor/requirements.txt`, `requirements-deploy.txt`).
- Manter execução transparente de `pytest`, scripts e build sem alterar lógicas de negócio.

**Non-Goals:**
- Alterar gerenciamento de pacotes local de desenvolvimento.

## Decisions

- **Substituição Total do `setup-python` por `setup-uv`**: Cada workflow contém apenas o step `astral-sh/setup-uv@v10` com os parâmetros:
  ```yaml
  - name: Setup uv e Python
    uses: astral-sh/setup-uv@v10
    with:
      version: "latest"
      python-version: "3.13"
      enable-cache: true
      cache-dependency-glob: |
        ...
  ```
- **Inclusão no Sparse Checkout**: Garantir que `requirements-deploy.txt` esteja presente no `sparse-checkout` do `pr-db-validator.yml` para resolução do `-r ../requirements-deploy.txt`.
- **Instalação no Ambiente do Sistema (`--system`)**: Utilizar `uv pip install --system -r <requirements>` garantindo que os executáveis e pacotes estejam imediatamente disponíveis no PATH do runner.

## Risks / Trade-offs

- **[Risco] Invalidação incorreta de cache**: Mitigado ao listar expressamente todos os arquivos de requirements relevantes no `cache-dependency-glob`.

## Migration Plan

1. Remover o step `Setup Python` (`actions/setup-python`) dos workflows afetados.
2. Adicionar o step unificado `Setup uv e Python` (`astral-sh/setup-uv@v10`) com `cache-dependency-glob` explícito.
3. Atualizar as linhas de comando para `uv pip install --system`.
4. Validar sintaxe YAML e compatibilidade dos pipelines.
