# Spec Delta

## MODIFIED Requirements

### Requirement: Empacotamento enxuto do executável do editor
O sistema SHALL gerar um pacote de distribuição em diretório (`onedir`) para Windows e macOS utilizando PyInstaller contendo estritamente as dependências necessárias para a execução da interface do editor, desativando a compressão UPX em tempo de execução para permitir carregamento instantâneo via memória mapeada no contêiner MSIX e pacote macOS, delegando a geração de distribuição no Linux integralmente ao ecossistema Flatpak.

#### Scenario: Compilação padrão em ambiente isolado
- **WHEN** o comando de compilação do editor (`editor/build.py dist`) for executado no Windows
- **THEN** o PyInstaller SHALL produzir um diretório de distribuição em `editor/dist/EditorAresta/` contendo o binário `EditorAresta.exe` e suas dependências descompactadas
- **THEN** o executável dentro do diretório gerado SHALL inicializar a interface gráfica normalmente sem requerer descompactação temporária em `%TEMP%`.

### Requirement: Cobertura total de testes unitários do processo de build
O módulo de compilação DEVE (SHALL) possuir 100% de cobertura de testes unitários em `editor/build_test.py`, testando de forma isolada a orquestração de distribuição, geração de argumentos e validação de ambiente sem código morto de filtragem de bibliotecas dinâmicas do Linux.

#### Scenario: Execução da suíte de testes de build
- **WHEN** a suíte de testes `pytest editor/build_test.py` for executada com medição de cobertura
- **THEN** a cobertura de código para `editor/build.py` deve ser de exatamente 100%

## ADDED Requirements

### Requirement: Orquestração do Flatpak no comando de distribuição do Linux
O utilitário `editor/build.py` DEVE (SHALL) suportar a ação `dist` no Linux delegando a compilação ao `flatpak-builder` e gerando o bundle `.flatpak` oficial em `editor/dist/`.

#### Scenario: Execução do build dist no Linux com flatpak-builder disponível
- **WHEN** o comando `editor/build.py dist` for executado no Linux com `flatpak-builder` instalado
- **THEN** o processo compila o manifesto em diretório de build isolado
- **AND** gera o arquivo `editor/dist/EditorAresta-<versao>.flatpak`
- **AND** exibe instruções de instalação local com `flatpak install --user`

#### Scenario: Execução do build dist no Linux sem flatpak-builder
- **WHEN** o comando `editor/build.py dist` for executado no Linux sem `flatpak-builder` no PATH
- **THEN** o processo encerra com código de erro não-zero
- **AND** exibe mensagem informativa em português orientando a instalação do pacote `flatpak-builder` na distribuição
