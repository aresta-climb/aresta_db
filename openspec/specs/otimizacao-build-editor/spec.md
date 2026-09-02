# otimizacao-build-editor Specification

## Purpose
TBD - created by archiving change otimizar-build-pyinstaller-editor. Update Purpose after archive.
## Requirements
### Requirement: Empacotamento enxuto do executável do editor
O sistema DEVE (SHALL) gerar um executável standalone para Windows utilizando PyInstaller contendo estritamente as dependências necessárias para a execução da interface do editor, mantendo o tamanho total do arquivo `.exe` abaixo de 95MB.

#### Scenario: Compilação padrão em ambiente isolado
- **WHEN** o comando de compilação do editor (`editor/build.py dist`) for executado
- **THEN** o executável gerado em `editor/dist/EditorAresta.exe` deve ter tamanho inferior a 95MB e inicializar a interface gráfica normalmente

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

