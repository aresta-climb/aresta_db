# Design: Migração do Editor Linux para Pure Flatpak

## Context

Atualmente, o Editor Aresta no Linux depende do PyInstaller para gerar um diretório congelado `onedir` contendo um interpretador Python embutido e dezenas de arquivos `.so` compilados no runner do Ubuntu. O script `editor/build.py` executa uma poda heurística (`filtrar_binarios_desnecessarios`) para tentar remover bibliotecas duplicadas do Qt e do sistema, o que causou falhas graves de runtime (como exclusão de dependências privadas em `.libs` e problemas de integração com D-Bus/keyring). O manifesto Flatpak apenas copiava esses arquivos remanescentes.

Para detalhes de motivação, consulte [proposal.md](proposal.md).

## Goals / Non-Goals

**Goals:**
- Adotar o padrão oficial do ecossistema Flatpak para aplicações PySide6 utilizando `io.qt.PySide.BaseApp` sobre `org.kde.Platform`.
- Executar a aplicação via Python nativo do runtime Flatpak (`python3 -m editor.main`), eliminando completamente o PyInstaller no Linux.
- Remover todo o código de poda de binários `.so` (`filtrar_binarios_desnecessarios`) de `editor/build.py`.
- Tornar o comando `python editor/build.py dist` um despachante universal que, no Linux, orquestra o `flatpak-builder` gerando o bundle `.flatpak`.
- Gerar o manifesto de dependências do Flathub (`pypi-dependencies.json`) dinamicamente no CI durante o deploy para o repositório `aresta-editor-flathub`, mantendo o `aresta_db` limpo de arquivos de dump.
- Manter 100% de cobertura de testes unitários em `editor/build_test.py`.

**Non-Goals:**
- Não alterar o empacotamento no Windows (PyInstaller -> MSIX) nem no macOS (PyInstaller -> DMG).
- Não manter suporte a arquivos `.tar.gz` de binários soltos para Linux (o Flatpak será o formato único).
- Não compilar dependências Python a partir do código-fonte C do zero quando houver wheels `manylinux` compatíveis.

## Decisions

### 1. Camada Base: `io.qt.PySide.BaseApp` + `org.kde.Platform` (6.8)
- **Decisão**: Utilizar o BaseApp oficial mantido pelo Flathub (`io.qt.PySide.BaseApp`) com versão `6.8` e runtime `org.kde.Platform` versão `6.8`.
- **Racional**: O BaseApp já fornece o interpretador Python 3 e o `PySide6` pré-compilados e perfeitamente linkados com a versão de Qt do KDE Platform. Isso elimina conflitos de ABI de Qt, reduz drasticamente o tamanho do bundle e evita que o pip tente compilar ou baixar wheels conflitantes de PySide6.
- **Alternativas consideradas**:
  - *Instalar PySide6 via pip no Flatpak simples*: Inviável em muitos casos porque o wheel oficial do PySide6 na PyPI inclui suas próprias cópias de bibliotecas Qt, causando colisões de símbolos com o runtime do sistema.

### 2. Estrutura do Módulo da Aplicação no Manifesto
- **Decisão**: O módulo da aplicação no manifesto Flatpak instala o código-fonte do editor em `/app/share/aresta-editor/` e cria um script executável em `/app/bin/EditorAresta`:
  ```bash
  #!/bin/sh
  export PYTHONPATH="/app/lib/python3.11/site-packages:/app/lib/python3.12/site-packages:/app/share/aresta-editor:$PYTHONPATH"
  exec python3 -m editor.main "$@"
  ```
- **Racional**: Garante execução Python 100% nativa, preservando `importlib.metadata`, descoberta dinâmica de plugins (`keyring` / `SecretServiceKeyring` / `KWallet`) e facilidade de depuração.

### 3. Gerenciamento e Ciclo de Vida do `pypi-dependencies.json`
- **Decisão**: O repositório `aresta_db` **não** versionará `pypi-dependencies.json`. A geração ocorre:
  1. **No CI de Release (`build_editor_linux.yml`)**: Exporta `uv export --only-group editor --no-dev --no-hashes > requirements.txt`, executa `flatpak-pip-generator` e commita o JSON resultante diretamente no repositório de publicação `aresta-editor-flathub`.
  2. **No Build Local (`editor/build.py dist`)**: O script gera temporariamente as dependências em cache local ou executa o `flatpak-builder` com flags locais caso o desenvolvedor esteja testando na máquina/VM.
- **Racional**: Mantém o `pyproject.toml` como única fonte da verdade e evita commits massivos de lixo gerado no histórico do monorepo.

### 4. Orquestração Unificada no `editor/build.py`
- **Decisão**: Limpar todas as rotinas de Linux do PyInstaller em `editor/build.py`. Quando `editor/build.py dist` for executado em ambiente Linux:
  - Verifica a presença do executável `flatpak-builder`. Se ausente, emite erro claro com instrução de instalação (ex: `sudo pacman -S flatpak-builder` ou `sudo apt install flatpak-builder`).
  - Executa o build isolado em `editor/dist/flatpak-build/`.
  - Exporta o pacote em `editor/dist/EditorAresta-<versao>.flatpak`.
- **Racional**: Proporciona uma interface de desenvolvedor consistente entre plataformas (`build.py dist` funciona em qualquer OS).

## Risks / Trade-offs

- **[Risco] Dependência de ferramentas Flatpak no host de desenvolvimento** → *Mitigação*: Desenvolvedores que apenas programam o editor utilizam `uv run python -m editor.main` normalmente. Apenas quem deseja gerar o pacote `.flatpak` local precisará de `flatpak-builder` e do runtime `org.kde.Platform` instalados.
- **[Risco] Incompatibilidade de pacotes C pesados no flatpak-pip-generator** → *Mitigação*: Nossas dependências de editor (`pygit2`, `pillow`, `cryptography`, `pillow-heif`) possuem wheels universais/manylinux modernos na PyPI. O `flatpak-pip-generator` suporta `--runtime` para resolver os hashes corretos de arquitetura x86_64.
- **[Risco] Quebra do CI se o app token do bot não tiver permissão no repo flathub** → *Mitigação*: O workflow já possui configuração de token GitHub App para clonar e atualizar `aresta-editor-flathub`.

## Migration Plan

1. Limpar `editor/build.py` e `editor/build_test.py` removendo as heurísticas de filtragem de `.so`.
2. Adaptar o `editor/build.py` para suportar o target Linux invocando `flatpak-builder`.
3. Atualizar `editor/flatpak/com.arestaclimb.Editor.yaml` para usar `io.qt.PySide.BaseApp` e launcher nativo.
4. Atualizar `.github/workflows/build_editor_linux.yml` para exportar dependências via `flatpak-pip-generator` e sincronizar com o Flathub sem PyInstaller.
5. Testar e validar a compilação local na VM Linux (Manjaro).
