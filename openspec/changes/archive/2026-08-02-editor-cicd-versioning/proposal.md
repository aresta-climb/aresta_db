## Why

Acabar com a compilação manual do editor na máquina dos desenvolvedores e garantir que o executável oficial seja gerado, versionado e distribuído sistematicamente via GitHub Releases. Isso estabelece a fundação de infraestrutura necessária para, futuramente, implementarmos travas de segurança no banco de dados e rotinas completas de auto-update.

## What Changes

- **Build Automatizado (CI/CD)**: Novo workflow no GitHub Actions que compila o editor (`.exe` via PyInstaller) sempre que acionado manualmente (`workflow_dispatch`).
- **Bump e Tagging**: O fluxo receberá a versão-alvo como input, fará o commit de bumping de versão e criará a tag Git correspondente (ex: `v1.2.3`). Após o lançamento, injetará a sufixação de desenvolvimento (`-dev`) para o próximo ciclo, espelhando a esteira já existente no `aresta_app`.
- **Injeção de Versão (Library-First / TDD)**: Durante a esteira, a versão será gravada em `editor/core/version.py` via um script em Python robusto e amplamente testado, ao invés de comandos shell frágeis, assegurando o princípio de Library-First e aderência a 100% de test coverage.
- **Orientação a Testes (TDD)**: Todo novo módulo (versão e injeção de versão) será desenvolvido sob a metodologia de TDD (Test-Driven Development), com testes escritos previamente à implementação, garantindo qualidade e simplicidade.
- **Publicação Automatizada**: O artefato `.exe` gerado será feito upload (anexado) a uma nova Release oficial do repositório correspondente à tag recém-criada.

## Capabilities

### New Capabilities
- `editor-cicd-pipeline`: A esteira de integração e entrega contínua (GitHub Actions) responsável por gerenciar versões e compilar o editor.
- `editor-versioning-module`: O arquivo ou módulo Python que expõe passivamente os atributos de versão compilada para o código-fonte do Editor Aresta.

### Modified Capabilities

## Impact

- Inclusão de novos workflows `.yml` dentro da pasta `.github/workflows/` (ou scripts auxiliares na raiz do projeto `aresta_db`).
- Alterações mínimas no código do editor para importar `version.py` caso seja necessário logar ou checar passivamente a versão atual num menu "Sobre".
- Processo de distribuição modernizado: os colaboradores baixarão o editor sempre da aba "Releases" do GitHub.
