# Spec Delta

## MODIFIED Requirements

### Requirement: Isolamento de dependências de IA e OCR
O pipeline de build do editor DEVE (SHALL) garantir que dependências externas pesadas não pertencentes ao grupo `editor` (como bibliotecas de visão computacional e IA `cv2`, `paddleocr`, `paddlex`, `scipy` e `torch`) não sejam incorporadas ao executável do editor, enquanto dependências integrantes do grupo `editor` e da compilação local do catálogo (incluindo `pymupdf`, `lxml`/`ddgs` e `sqlite3`) DEVEM (SHALL) ser integralmente empacotadas em todas as plataformas (Windows, macOS e Linux), removendo apenas arquivos de cabeçalho e desenvolvimento de tempo de compilação (`mupdf-devel`).

#### Scenario: Verificação de ausência de módulos pesados no pacote
- **WHEN** o pacote do executável for inspecionado após a compilação
- **THEN** nenhum módulo ou binário de `cv2`, `paddleocr`, `paddlex`, `scipy` ou `torch` deve estar presente no bundle do PyInstaller
- **AND** os módulos e extensões nativas de `pymupdf`, `lxml` e `sqlite3` devem estar presentes e operacionais no pacote gerado, sem incluir o diretório de cabeçalhos `mupdf-devel`.

### Requirement: Cobertura total de testes unitários do processo de build
O módulo de compilação DEVE (SHALL) possuir 100% de cobertura comportamental em `editor/build_test.py` sem utilizar mocks para bibliotecas internas, sistema de arquivos (`Path`) ou processamento de imagens (`PIL`), validando automaticamente a consistência entre o lockfile do grupo `editor`, o grafo de importações do código de produção, a lista de exclusões e o arquivo `EditorAresta.spec`.

#### Scenario: Execução da suíte de testes de build
- **WHEN** a suíte de testes `pytest editor/build_test.py` for executada com medição de cobertura
- **THEN** a cobertura de código para `editor/build.py` deve ser de exatamente 100% sem mocks de componentes internos.

#### Scenario: Invariante de não-interseção entre dependências do editor e módulos excluídos
- **WHEN** os testes de empacotamento verificarem a lista de módulos excluídos do build
- **THEN** nenhum pacote pertencente à exportação do grupo `editor` no `uv.lock` nem qualquer módulo importado pelos pacotes de produção (`editor`, `coleta_de_betas` e `migracoes`) deve ser bloqueado pela lista de exclusões
- **AND** todos os módulos declarados explicitamente em `hiddenimports` na especificação de empacotamento devem existir e ser importáveis.
