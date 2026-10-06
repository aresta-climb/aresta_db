# Spec Delta

## MODIFIED Requirements

### Requirement: Manifesto Flatpak Oficial e Identificador de Aplicação
O repositório DEVE (SHALL) fornecer um manifesto Flatpak determinístico sob o identificador `com.arestaclimb.Editor` e arquivo de metadados AppStream (`com.arestaclimb.Editor.metainfo.xml`), utilizando `io.qt.PySide.BaseApp` e runtime `org.kde.Platform` para compilação nativa no Flathub sem intermediate de executável congelado por PyInstaller.

#### Scenario: Validação do manifesto Flatpak
- **WHEN** o manifesto `com.arestaclimb.Editor.yaml` for validado com ferramentas Flatpak
- **THEN** o arquivo declara `base: io.qt.PySide.BaseApp` e `runtime: org.kde.Platform`
- **AND** a execução do aplicativo invoca diretamente o interpretador Python (`python3 -m editor.main`) em `/app/bin/EditorAresta`
- **AND** os metadados AppStream incluem resumo em português, licença e categorias compatíveis com as lojas de aplicativos do Linux

## ADDED Requirements

### Requirement: Resolução Automática de Dependências Python para Flathub
O pipeline de distribuição Linux DEVE (SHALL) gerar a lista declarativa de fontes de dependências Python (`pypi-dependencies.json`) a partir do grupo `editor` do `pyproject.toml` exclusivamente durante o processo de exportação/deploy para o repositório Flathub, sem versionar arquivos de dump de pacotes no repositório `aresta_db`.

#### Scenario: Exportação de manifesto de dependências no CI
- **WHEN** o workflow de release do Linux for executado
- **THEN** as dependências do grupo `editor` são extraídas e convertidas pelo gerador Flatpak
- **AND** o arquivo de dependências é sincronizado diretamente no repositório de publicação `aresta-editor-flathub`
- **AND** o repositório `aresta_db` não armazena o artefato JSON gerado

### Requirement: Formato Único de Distribuição Linux via Flatpak
O ecossistema Linux DEVE (SHALL) disponibilizar o Editor Aresta exclusivamente via pacote Flatpak (repositório Flathub e bundle offline `.flatpak`), descontinuando o empacotamento e distribuição de arquivos `.tar.gz` de binários onedir.

#### Scenario: Geração de pacote instalável no Linux
- **WHEN** o processo de distribuição para Linux for finalizado
- **THEN** o artefato de instalação gerado em `editor/dist/` deve ser um bundle `.flatpak`
- **AND** nenhum tarball contendo binário do PyInstaller deve ser publicado para Linux
