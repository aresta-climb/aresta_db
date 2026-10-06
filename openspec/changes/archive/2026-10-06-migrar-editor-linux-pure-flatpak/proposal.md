# Proposal

## Why

O empacotamento do Editor Aresta no Linux utiliza atualmente uma arquitetura híbrida frágil: o PyInstaller gera um diretório congelado (`onedir`), um script em `editor/build.py` tenta remover dezenas de arquivos `.so` heurísticamente para evitar conflito com o runtime KDE, e o Flatpak apenas empacota esse binário remanescente. Essa abordagem causa falhas frequentes em tempo de execução (como remoção acidental de dependências vendored em `.libs`, incompatibilidade de ABI e quebra de descoberta de plugins pelo `keyring`), além de violar as diretrizes oficiais de compilação limpa e reproduzível do Flathub.

A migração para um modelo Pure Flatpak no Linux elimina o PyInstaller nesse sistema operacional, adotando o padrão da comunidade (`io.qt.PySide.BaseApp`) com execução Python nativa e gerenciamento automático de dependências, garantindo estabilidade universal em qualquer distribuição Linux.

## What Changes

- **Abandono do PyInstaller no Linux**: O PyInstaller deixa de ser utilizado no Linux, permanecendo restrito ao empacotamento no Windows (MSIX) e macOS (DMG).
- **Remoção de filtragem manual de binários `.so`**: Exclusão de `filtrar_binarios_desnecessarios` e heurísticas manuais de exclusão de bibliotecas dinâmicas de `editor/build.py`.
- **Pure Flatpak com BaseApp Oficial**: O manifesto `editor/flatpak/com.arestaclimb.Editor.yaml` passa a utilizar `base: io.qt.PySide.BaseApp` sobre `runtime: org.kde.Platform`, executando o interpretador Python e o PySide6 de forma nativa.
- **Orquestração Universal via `editor/build.py dist`**: No Linux, o comando `python editor/build.py dist` passa a invocar o `flatpak-builder` para gerar o bundle `.flatpak` em `editor/dist/`, mantendo uma interface de linha de comando única entre plataformas.
- **Pipeline de Dependências no CI**: O workflow `.github/workflows/build_editor_linux.yml` passa a converter dependências do grupo `editor` (via `uv export` e `flatpak-pip-generator`) diretamente no repositório de publicação `aresta-editor-flathub`, sem poluir o repositório principal `aresta_db`.
- **Flatpak como Formato Único no Linux**: Remoção da geração de tarballs `.tar.gz` genéricos com binários congelados no Linux.

## Capabilities

### New Capabilities

*(Nenhuma nova capacidade durable criada; as capacidades existentes de empacotamento e distribuição cobrem esse domínio.)*

### Modified Capabilities

- `editor-distribuicao-linux`: Substituição do modelo de binário congelado por empacotamento Flatpak nativo baseado em `io.qt.PySide.BaseApp`, com resolução de dependências Python limpa e execução nativa no sandbox.
- `otimizacao-build-editor`: Redefinição do alvo Linux em `editor/build.py dist` para orquestrar o `flatpak-builder` em vez do PyInstaller, expurgando a filtragem frágil de arquivos `.so`.

## Impact

- **Código afetado**: `editor/build.py`, `editor/build_test.py`, `editor/flatpak/com.arestaclimb.Editor.yaml`, `.github/workflows/build_editor_linux.yml`.
- **Dependências**: Eliminação de `pyinstaller` como pré-requisito de runtime de empacotamento no Linux. Introdução de `flatpak-builder` no host Linux para compilação local de distribuição.
- **Compatibilidade**: Elimina falhas de importação de extensões C (ex: Pillow, pygit2) e de cofre de credenciais (`keyring` / D-Bus). O pacote `.flatpak` torna-se o único artefato de distribuição para distribuições Linux.
