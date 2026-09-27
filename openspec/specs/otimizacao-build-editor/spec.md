# otimizacao-build-editor Specification

## Purpose
TBD - created by archiving change otimizar-build-pyinstaller-editor. Update Purpose after archive.
## Requirements
### Requirement: Empacotamento enxuto do executável do editor
O sistema SHALL gerar um pacote de distribuição em diretório (`onedir`) para Windows utilizando PyInstaller contendo estritamente as dependências necessárias para a execução da interface do editor, desativando a compressão UPX em tempo de execução para permitir carregamento instantâneo via memória mapeada no contêiner MSIX.

#### Scenario: Compilação padrão em ambiente isolado
- **WHEN** o comando de compilação do editor (`editor/build.py dist`) for executado
- **THEN** o PyInstaller SHALL produzir um diretório de distribuição em `editor/dist/EditorAresta/` contendo o binário `EditorAresta.exe` e suas dependências descompactadas
- **THEN** o executável dentro do diretório gerado SHALL inicializar a interface gráfica normalmente sem requerer descompactação temporária em `%TEMP%`.

### Requirement: Empacotamento MSIX a partir de diretório onedir
O pipeline de integração e empacotamento MSIX SHALL coletar o diretório de distribuição `onedir` gerado pelo PyInstaller e empacotá-lo diretamente no contêiner de instalação sem etapas intermediárias de extração em tempo de execução.

#### Scenario: Empacotamento do contêiner MSIX
- **WHEN** o workflow de release do editor empacotar os artefatos de build
- **THEN** o conteúdo completo do diretório `editor/dist/EditorAresta/` SHALL ser copiado para o diretório de staging do MSIX
- **THEN** o arquivo `.msix` gerado SHALL instalar a aplicação com acesso direto aos binários mapeados em disco.

### Requirement: Isolamento de dependências de IA e OCR
O pipeline de build do editor DEVE (SHALL) garantir que dependências externas pertencentes a outros grupos (como bibliotecas de visão computacional `cv2`, `paddleocr`, `pymupdf` e `scipy`) não sejam incorporadas ao executável do editor.

#### Scenario: Verificação de ausência de módulos pesados no pacote
- **WHEN** o pacote do executável for inspecionado após a compilação
- **THEN** nenhum módulo ou binário de `cv2`, `paddleocr`, `pymupdf`, `paddlex` ou `scipy` deve estar presente no bundle do PyInstaller

### Requirement: Remoção de binários redundantes do PySide6
O processo de build DEVE (SHALL) filtrar e remover DLLs de fallback de hardware como `opengl32sw.dll` e submódulos gráficos não utilizados do Qt (como `QtQuick`, `QtQml`, `QtPdf`).

#### Scenario: Poda de binários no build
- **WHEN** a análise do PyInstaller for executada sobre o `EditorAresta.spec`
- **THEN** a DLL `opengl32sw.dll` deve ser excluída da lista de binários empacotados

### Requirement: Cobertura total de testes unitários do processo de build
O módulo de compilação DEVE (SHALL) possuir 100% de cobertura de testes unitários em `editor/build_test.py`, testando de forma isolada a geração de argumentos, filtragem de binários e validação de ambiente.

#### Scenario: Execução da suíte de testes de build
- **WHEN** a suíte de testes `pytest editor/build_test.py` for executada com medição de cobertura
- **THEN** a cobertura de código para `editor/build.py` deve ser de exatamente 100%

