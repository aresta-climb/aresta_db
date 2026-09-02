## Why

Após a migração do PyQt6 para o PySide6 e a introdução de novas dependências no repositório (OCR, visão computacional e inteligência artificial para processamento de PDFs), o executável standalone do Editor Aresta gerado pelo PyInstaller saltou de ~75MB para mais de 260MB.

Esse tamanho excessivo prejudica o download, o tempo de distribuição e o consumo de armazenamento dos usuários finais. Precisamos otimizar a cadeia de compilação para empacotar estritamente o runtime necessário do Editor, restaurando o tamanho do binário para a faixa de ~75MB a 85MB.

## What Changes

- Substituição da dependência `pyside6` por `pyside6-essentials` no grupo `editor` do `pyproject.toml`, eliminando módulos desnecessários do Qt (como QtWebEngine, Qt3D, QtMultimedia).
- Estruturação modular da lógica de configuração de build no `editor/build.py` (Library-First) para permitir testes unitários isolados com 100% de cobertura.
- Configuração do pipeline de build para isolar o ambiente com `uv` (`--isolated --no-default-groups --group editor`), impedindo o vazamento de dependências de IA/OCR/PDF (`paddleocr`, `cv2`, `pymupdf`, `scipy`) para o executável.
- Poda de binários pesados de fallback do PySide6 (como `opengl32sw.dll` de ~20MB) e exclusão explícita de submódulos Qt não utilizados no arquivo de especificação do PyInstaller.
- Adição de testes de integração e testes unitários seguindo TDD em `editor/build_test.py` para garantir 100% de cobertura e que o executável gerado permaneça estritamente abaixo do limite de tamanho estipulado (< 95MB).

## Capabilities

### New Capabilities
- `otimizacao-build-editor`: Especifica os requisitos de empacotamento enxuto, isolamento de dependências e limite máximo de tamanho para o executável standalone do Editor Aresta.

### Modified Capabilities
- `editor-cicd-pipeline`: Atualiza o requisito de automação de lançamento do editor para utilizar o ambiente isolado do grupo `editor` e dependências mínimas do PySide6.

## Impact

- **Dependências (`pyproject.toml`)**: Grupo `editor` passa a exigir `pyside6-essentials` em vez do meta-pacote `pyside6`.
- **Scripts de Build (`editor/build.py`, `editor/EditorAresta.spec`)**: Configuração modularizada de análise e exclusão de binários com 100% de cobertura de testes.
- **Tamanho do Executável**: Redução drástica de ~260MB para ~80MB no Windows.
