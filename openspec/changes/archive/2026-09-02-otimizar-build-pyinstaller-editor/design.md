## Context

Após a transição de bindings de interface gráfica do PyQt6 para o PySide6 e a adição de ferramentas pesadas de processamento de documentos (PaddleOCR, PaddleX, OpenCV, PyMuPDF, SciPy) para tarefas de ingestão de dados, o executável do Editor Aresta gerado pelo PyInstaller saltou de ~75MB para 257.66MB.

A investigação revelou que:
1. O meta-pacote `pyside6` inclui `pyside6-addons` com módulos pesados C++ (como QtWebEngine, Qt3D, QtMultimedia).
2. O ambiente local de desenvolvimento instala todos os grupos de dependências juntos, permitindo que o PyInstaller analise estaticamente e empacote submódulos de visão computacional e OCR importados indiretamente por scripts.
3. O hook padrão do PySide6 no PyInstaller coleta DLLs pesadas de compatibilidade (como `opengl32sw.dll` de 19.7MB).

## Goals / Non-Goals

**Goals:**
- Reduzir o tamanho final do executável standalone do Editor Aresta de ~260MB para <= 90MB (idealmente entre 75MB e 85MB).
- Automatizar o isolamento do build via `uv` para que nenhuma biblioteca externa de IA/OCR/PDF seja empacotada.
- Adotar `pyside6-essentials` em substituição a `pyside6` nas dependências do editor.
- Limpar a especificação de empacotamento (`EditorAresta.spec` e `editor/build.py`) com funções modulares e puras (Library-First) para excluir explicitamente binários e submódulos gráficos desnecessários.
- Desenvolver toda a implementação seguindo estritamente TDD (Test-Driven Development), com testes de integração e 100% de cobertura de testes unitários.

**Non-Goals:**
- Migrar o pipeline de empacotamento para Nuitka nesta fase (manteremos o PyInstaller devido à estabilidade e tempo de compilação de ~15 segundos).
- Modificar o comportamento visual ou funcional da interface do Editor Aresta.
- Remover as ferramentas de OCR/PDF do repositório (elas continuarão isoladas em seu próprio grupo de dependências `pdf`).

## Decisions

### 1. Migração para `pyside6-essentials` no grupo `editor`
- **Decisão**: Alterar `pyproject.toml` no grupo `editor` de `pyside6` para `pyside6-essentials`.
- **Justificativa**: O Editor Aresta necessita exclusivamente de `QtCore`, `QtGui`, `QtWidgets`, `QtNetwork`, `QtSvg` e `QtXml`. O `pyside6-essentials` contém todos esses módulos sem carregar os 400MB+ de bibliotecas do `pyside6-addons`.
- **Alternativa considerada**: Manter `pyside6` e excluir cada submódulo manualmente. Rejeitada por ser frágil e propensa a quebrar com atualizações do Qt.

### 2. Isolamento de ambiente com `uv run --isolated` no pipeline de build
- **Decisão**: Configurar a chamada de compilação para executar em ambiente isolado contendo unicamente o grupo `editor`.
- **Justificativa**: Garante que pacotes pesados como `opencv-contrib-python`, `paddleocr`, `pymupdf` e `scipy` não estejam presentes no `site-packages` durante o rastreamento de AST do PyInstaller.
- **Alternativa considerada**: Adicionar dezenas de argumentos `--exclude-module` no script. Rejeitada porque novas dependências adicionadas a outros grupos poderiam vazar silenciosamente no futuro.

### 3. Modularização da lógica de build e poda de binários (Library-First)
- **Decisão**: Extrair funções puras e modulares em `editor/build.py` (como `obter_argumentos_pyinstaller`, `filtrar_binarios_desnecessarios` e `obter_modulos_excluidos`).
- **Justificativa**: Permite testar cada regra de filtragem e configuração de forma unitária, isolada e determinística, atingindo 100% de cobertura de testes conforme preconizado no `PRINCIPIOS.md`.
- **Poda de DLLs**: A função de filtragem remove `opengl32sw.dll` (renderizador Mesa OpenGL de quase 20MB dispensável em sistemas modernos) e eventuais DLLs do QML/Quick.

### 4. Imperativo de TDD e 100% de Cobertura de Testes
- **Decisão**: Escrever os testes em `editor/build_test.py` antes de alterar a implementação de `editor/build.py` e `EditorAresta.spec`.
- **Justificativa**: Segue o fluxo obrigatório Red-Green-Refactor, garantindo que o comportamento esperado de filtragem, flags de build e validação de tamanho estejam garantidos antes do código de produção.

## Aderência aos Princípios de Engenharia (`PRINCIPIOS.md`)

| Princípio | Aplicação no Design |
| :--- | :--- |
| **I. Tudo em Português** | Todos os nomes de funções (`obter_argumentos_pyinstaller`, `filtrar_binarios_desnecessarios`), variáveis, documentações e especificações são 100% em português brasileiro. |
| **II. Library-First** | As rotinas de geração de argumentos e filtragem de binários do PyInstaller são estruturadas como funções puras e reutilizáveis, desacopladas de I/O de terminal. |
| **III. 100% Unit Test Coverage** | Todos os novos métodos e ramos condicionais em `editor/build.py` possuem cobertura completa em `editor/build_test.py`. |
| **IV. TDD (Test-Driven Development)** | Testes criados no padrão Red-Green-Refactor antes de qualquer alteração nos arquivos de build. |
| **V. Testes de Integração em Primeiro Lugar** | Teste de integração do build compilando o pacote e verificando tamanho e executabilidade antes dos testes de unidade profundos. |
| **VI. Simplicidade e Anti-Abstração** | Funções diretas e declarativas, sem factories genéricas ou complexidade acidental. |

## Risks / Trade-offs

- **[Risco] Falta de componentes do Qt em runtime**: Se algum diálogo ou recurso utilizar dinamicamente um módulo fora do `pyside6-essentials` (ex: SVG ou Impressão).
  - *Mitigação*: A suíte de testes de UI do editor (`pytest editor/`) e testes manuais de exportação cobrem a interface e garantem que `pyside6-essentials` supre 100% das necessidades.
- **[Risco] Máquinas antigas sem aceleração OpenGL para `opengl32sw.dll`**: Usuários com drivers gráficos ausentes poderiam sofrer problemas de renderização.
  - *Mitigação*: O Qt 6 no Windows utiliza o backend gráfico padrão ANGLE/D3D11 do sistema operacional, tornando o fallback Mesa desnecessário para aplicações QtWidgets tradicionais.
