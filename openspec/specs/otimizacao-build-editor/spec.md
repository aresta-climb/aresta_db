# otimizacao-build-editor Specification

## Purpose
Define os requisitos de otimização de compilação, poda de dependências pesadas e empacotamento do executável do editor para Windows, macOS e Linux.
## Requirements
### Requirement: Empacotamento enxuto do executável do editor
O sistema SHALL gerar um pacote de distribuição em diretório (`onedir`) para Windows e macOS utilizando PyInstaller contendo estritamente as dependências necessárias para a execução da interface do editor, desativando a compressão UPX em tempo de execução para permitir carregamento instantâneo via memória mapeada no contêiner MSIX e pacote macOS, delegando a geração de distribuição no Linux integralmente ao ecossistema Flatpak.

#### Scenario: Compilação padrão em ambiente isolado
- **WHEN** o comando de compilação do editor (`editor/build.py dist`) for executado no Windows
- **THEN** o PyInstaller SHALL produzir um diretório de distribuição em `editor/dist/EditorAresta/` contendo o binário `EditorAresta.exe` e suas dependências descompactadas
- **THEN** o executável dentro do diretório gerado SHALL inicializar a interface gráfica normalmente sem requerer descompactação temporária em `%TEMP%`.

### Requirement: Empacotamento MSIX a partir de diretório onedir
O pipeline de integração e empacotamento MSIX SHALL coletar o diretório de distribuição `onedir` gerado pelo PyInstaller e empacotá-lo diretamente no contêiner de instalação sem etapas intermediárias de extração em tempo de execução.

#### Scenario: Empacotamento do contêiner MSIX
- **WHEN** o workflow de release do editor empacotar os artefatos de build
- **THEN** o conteúdo completo do diretório `editor/dist/EditorAresta/` SHALL ser copiado para o diretório de staging do MSIX
- **THEN** o arquivo `.msix` gerado SHALL instalar a aplicação com acesso direto aos binários mapeados em disco.

### Requirement: Isolamento de dependências de IA e OCR
O pipeline de build do editor DEVE (SHALL) garantir que dependências externas pesadas não pertencentes ao grupo `editor` (como bibliotecas de visão computacional e IA `cv2`, `paddleocr`, `paddlex`, `scipy` e `torch`) não sejam incorporadas ao executável do editor, enquanto dependências integrantes do grupo `editor` e da compilação local do catálogo (incluindo `pymupdf`, `lxml`/`ddgs` e `sqlite3`) DEVEM (SHALL) ser integralmente empacotadas em todas as plataformas (Windows, macOS e Linux), removendo apenas arquivos de cabeçalho e desenvolvimento de tempo de compilação (`mupdf-devel`).

#### Scenario: Verificação de ausência de módulos pesados no pacote
- **WHEN** o pacote do executável for inspecionado após a compilação
- **THEN** nenhum módulo ou binário de `cv2`, `paddleocr`, `paddlex`, `scipy` ou `torch` deve estar presente no bundle do PyInstaller
- **AND** os módulos e extensões nativas de `pymupdf`, `lxml` e `sqlite3` devem estar presentes e operacionais no pacote gerado, sem incluir o diretório de cabeçalhos `mupdf-devel`.

### Requirement: Remoção de binários redundantes do PySide6
O processo de build DEVE (SHALL) filtrar e remover DLLs de fallback de hardware como `opengl32sw.dll` e submódulos gráficos não utilizados do Qt (como `QtQuick`, `QtQml`, `QtPdf`).

#### Scenario: Poda de binários no build
- **WHEN** a análise do PyInstaller for executada sobre o `EditorAresta.spec`
- **THEN** a DLL `opengl32sw.dll` deve ser excluída da lista de binários empacotados

### Requirement: Cobertura total de testes unitários do processo de build
O módulo de compilação DEVE (SHALL) possuir 100% de cobertura comportamental em `editor/build_test.py` sem utilizar mocks para bibliotecas internas, sistema de arquivos (`Path`) ou processamento de imagens (`PIL`), validando automaticamente a consistência entre o lockfile do grupo `editor`, o grafo de importações do código de produção, a lista de exclusões e o arquivo `EditorAresta.spec`.

#### Scenario: Execução da suíte de testes de build
- **WHEN** a suíte de testes `pytest editor/build_test.py` for executada com medição de cobertura
- **THEN** a cobertura de código para `editor/build.py` deve ser de exatamente 100% sem mocks de componentes internos.

#### Scenario: Invariante de não-interseção entre dependências do editor e módulos excluídos
- **WHEN** os testes de empacotamento verificarem a lista de módulos excluídos do build
- **THEN** nenhum pacote pertencente à exportação do grupo `editor` no `uv.lock` nem qualquer módulo importado pelos pacotes de produção (`editor`, `coleta_de_betas` e `migracoes`) deve ser bloqueado pela lista de exclusões
- **AND** todos os módulos declarados explicitamente em `hiddenimports` na especificação de empacotamento devem existir e ser importáveis.

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

