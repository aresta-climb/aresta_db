## MODIFIED Requirements

### Requirement: Empacotamento enxuto do executável do editor
O sistema SHALL gerar um pacote de distribuição em diretório (`onedir`) para Windows utilizando PyInstaller contendo estritamente as dependências necessárias para a execução da interface do editor, desativando a compressão UPX em tempo de execução para permitir carregamento instantâneo via memória mapeada no contêiner MSIX.

#### Scenario: Compilação padrão em ambiente isolado
- **WHEN** o comando de compilação do editor (`editor/build.py dist`) for executado
- **THEN** o PyInstaller SHALL produzir um diretório de distribuição em `editor/dist/EditorAresta/` contendo o binário `EditorAresta.exe` e suas dependências descompactadas
- **THEN** o executável dentro do diretório gerado SHALL inicializar a interface gráfica normalmente sem requerer descompactação temporária em `%TEMP%`.

## ADDED Requirements

### Requirement: Empacotamento MSIX a partir de diretório onedir
O pipeline de integração e empacotamento MSIX SHALL coletar o diretório de distribuição `onedir` gerado pelo PyInstaller e empacotá-lo diretamente no contêiner de instalação sem etapas intermediárias de extração em tempo de execução.

#### Scenario: Empacotamento do contêiner MSIX
- **WHEN** o workflow de release do editor empacotar os artefatos de build
- **THEN** o conteúdo completo do diretório `editor/dist/EditorAresta/` SHALL ser copiado para o diretório de staging do MSIX
- **THEN** o arquivo `.msix` gerado SHALL instalar a aplicação com acesso direto aos binários mapeados em disco.
