## Why

Atualmente, o Editor Aresta está restrito ao ecossistema Windows (distribuído na Microsoft Store para a track principal e via AppInstaller/MSIX no Cloudflare R2 para a track beta). Usuários e mantenedores que utilizam Linux e macOS não conseguem rodar o editor de forma nativa e empacotada. 
Esta mudança expande o Editor Aresta para Linux (via Flathub/Flatpak) e macOS (binário nativo ARM64 notarizado com auto-update via Sparkle no Cloudflare R2) em uma track oficial única de deploy contínuo, mantendo a arquitetura limpa, desacoplada por plataforma e estritamente aderente aos Princípios de Engenharia Aresta (Tudo em Português, Library-First, TDD, 100% de cobertura, Testes de Integração em primeiro lugar e Simplicidade).

## What Changes

- **Isolamento de Plataforma (`editor/plataforma/`):** Centralização de todo o código dependente de sistema operacional (Win32, WinRT, macOS Sparkle, Linux XDG/Portal) como uma biblioteca independente (`editor/plataforma/`), expondo uma interface pública agnóstica para o restante da base de código, inteiramente em português brasileiro.
- **Testes de Integração e Fronteiras em Primeiro Lugar (AST Lint Test):** Teste de integração de fronteiras (`tests/fronteiras_plataforma_test.py`) estabelecido antes das implementações unitárias, validando estaticamente que nenhum arquivo fora de `editor/plataforma/` importa APIs nativas ou módulos específicos de sistema operacional.
- **Empacotamento e Distribuição macOS:**
  - Suporte à compilação de binários nativos ARM64 (`.app` e `.dmg`) via PyInstaller.
  - Assinatura digital com certificado Apple *Developer ID Application* e notarização automatizada via `xcrun notarytool`.
  - Integração com o *Sparkle Framework* para verificação e atualização in-app silenciosa/automática alimentada por feed `appcast.xml` hospedado no Cloudflare R2.
  - Track única de lançamento direto (sem necessidade de canal beta separado).
- **Empacotamento e Distribuição Linux:**
  - Criação do manifesto oficial Flatpak (`com.arestaclimb.Editor.yaml`) e metadados AppStream.
  - Publicação na track única de produção do Flathub com buildbot automatizado.
- **Isolamento do Diretório de Dados:** Padronização do diretório canônico de dados `EditorAresta` por plataforma (`~/.local/share/EditorAresta` no Linux e `~/Library/Application Support/EditorAresta` no macOS).
- **Extensão do Pipeline CI/CD:** Atualização do workflow do GitHub Actions para incluir matriz de compilação e publicação multiplataforma (`ubuntu-latest` e `macos-14` ARM64) ao lado do Windows.
- **Conformidade com TDD e Cobertura:** Todo arquivo `.py` introduzido ou modificado possui obrigatoriamente seu respectivo `_test.py` no mesmo diretório, garantindo 100% de cobertura de testes unitários.

## Capabilities

### New Capabilities
- `editor-plataforma-abstracao`: Arquitetura de fachada agnóstica sob `editor/plataforma/`, com submódulos específicos para Windows, Linux e macOS, acompanhada de teste de fronteiras de importação via AST.
- `editor-distribuicao-macos`: Pipeline de empacotamento `.dmg` para Apple Silicon (ARM64), assinatura, notarização oficial da Apple e auto-atualização in-app através do Sparkle Framework com feed no Cloudflare R2.
- `editor-distribuicao-linux`: Manifesto Flatpak e metadados AppStream para compilação e distribuição do Editor Aresta na rede Flathub.

### Modified Capabilities
- `editor-cicd-pipeline`: Expansão do workflow de lançamento para orquestrar os builds de Linux e macOS em conjunto com as tracks existentes de Windows.

## Impact

- **Código-fonte:** Migração e refatoração de `editor/core/integracao_windows.py` e `editor/core/servico_loja.py` para dentro de `editor/plataforma/windows/`, além de ajustes em `editor/build.py` para suportar exclusões de bibliotecas dinâmicas Unix (`.so`, `.dylib`).
- **Dependências:** Inclusão condicional de frameworks/ferramentas de empacotamento no macOS e Linux no `pyproject.toml` se necessário.
- **CI/CD e Secrets:** Configuração de segredos da Apple no GitHub Actions (`APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID`, certificado P12 Developer ID) e chave de assinatura do Sparkle (Ed25519).
