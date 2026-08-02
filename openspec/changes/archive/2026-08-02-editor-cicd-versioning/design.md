## Context

O Aresta Editor é atualmente compilado manualmente a partir de scripts locais e distribuído informalmente para a equipe. Isso resulta em incerteza quanto ao estado real do código no momento em que um binário é gerado, e propicia a distribuição de versões sem um controle rígido de histórico (tags Git). A ausência dessa fundação impede a futura implantação de lógicas como o bloqueio da ferramenta quando desatualizada.

## Goals / Non-Goals

**Goals:**
- Implementar integração contínua (CI/CD) para gerar os artefatos do editor via GitHub Actions sempre que um lançamento manual for agendado.
- Adotar um fluxo de desenvolvimento versionado, onde a base de código sempre ostenta a sufixação de desenvolvimento (`-dev`), e as releases recebem tags limpas e consistentes.
- Distribuir o `.exe` oficialmente na página de Releases do repositório, atrelado a uma tag de Git clara.

**Non-Goals:**
- Lógicas ativas de auto-update, auto-instalação ou impedimento de publicações *por dentro* do executável (tais escopos são de responsabilidade das fases 2 e 3 de modernização).
- Compilar binários para macOS e Linux nesta primeira etapa (focaremos estritamente no build `--onefile` para Windows).

## Decisions

1. **Workflow Dispatch com Inputs Parametrizados**
   - *Rationale*: A equipe já está habituada com o modelo do `aresta_app`, e a criação de releases ainda necessita de supervisão humana.
   - *Abordagem*: Criaremos `.github/workflows/release_editor.yml`. O gatilho principal exigirá inputs como a nova versão exata (`new_version`).

2. **Injeção Transiente via Módulo Python**
   - *Rationale*: Arquivos `.json` soltos podem ser apagados pelo usuário ou esquecidos durante a cópia. Precisamos fixar a versão para dentro do pacote congelado pelo PyInstaller.
   - *Abordagem*: Imediatamente antes de invocar o PyInstaller na esteira, utilizaremos um script Python testável (ex: `editor/release_tools/bump_version.py`) para atualizar `editor/core/version.py` com constantes rígidas (`VERSION = '1.2.3'`). Essa ferramenta seguirá os Princípios de Engenharia Aresta (Library-First, TDD e 100% de test coverage).

3. **Ciclo Pós-Build Automático (`-dev`)**
   - *Rationale*: Preservar a linearidade da branch principal evitando que o código em desenvolvimento afirme já ser a versão final.
   - *Abordagem*: O workflow efetuará dois commits fundamentais durante a esteira (necessitando das devidas permissões de branch protection/Bot Token):
     - Passo 1: Commit com a versão fixa, seguido do `git tag v1.2.3`.
     - Passo 2: Mudança da versão local para `1.3.0-dev` e novo commit direto na branch que originou a pipeline (geralmente `main`).

## Risks / Trade-offs

- **[Risk] Bloqueios por restrições do PyInstaller no Runner Windows** → *Mitigation*: O GitHub Hosted Runner `windows-latest` costuma compilar executáveis de PyQt satisfatoriamente. Em caso de lentidão ou crash, ajustes finos nos pacotes ou uso de `actions/setup-python` com caching resolverão.
- **[Risk] Permissões do Github Token** → *Mitigation*: Será necessário assegurar que o token utilizado pelo action (`GITHUB_TOKEN` com `permissions: contents: write` ou um Token de App igual ao do front) tenha privilégios para burlar temporariamente eventuais proteções na `main` branch, se houver.
