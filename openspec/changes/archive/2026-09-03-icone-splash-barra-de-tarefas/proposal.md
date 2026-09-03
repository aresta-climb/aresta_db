## Why

Atualmente, durante a exibição da tela de abertura (`TelaDeAbertura`), o aplicativo exibe na barra de tarefas do Windows o ícone padrão genérico do sistema operacional (uma janela branca com cabeçalho azul), em vez do ícone oficial do Aresta Climb. O logo oficial só passa a ser exibido posteriormente quando a janela de seleção de croquis (`TelaDeCarregamento`) é aberta.

Isso ocorre porque a `TelaDeAbertura` utiliza a flag `Qt.WindowType.FramelessWindowHint`, fazendo com que o Windows a instancie nativamente como uma janela `WS_POPUP` sem `WS_CAPTION` e sem o estilo estendido `WS_EX_APPWINDOW`. Pelas regras da Shell do Windows, janelas com essas características não são associadas a botões da barra de tarefas. Como o processo registra um identificador explícito (`SetCurrentProcessExplicitAppUserModelID("aresta.editor.v1")`), o Windows cria um botão reservado na barra de tarefas para o aplicativo, mas não encontra nenhuma janela qualificada para obter o ícone via `WM_GETICON`, recorrendo ao ícone padrão genérico do sistema operacional.

## What Changes

Seguindo o princípio **Library-First** de `PRINCIPIOS.md`, a lógica de interoperabilidade com o sistema operacional não será acoplada diretamente na camada de visualização gráfica. Em vez disso:

- **Biblioteca Isolada de Integração (`editor/core/integracao_windows.py`)**: Criação de uma biblioteca dedicada, autossuficiente e testável de forma unitária, responsável por configurar a presença e os estilos de janelas na barra de tarefas do Windows (`WS_EX_APPWINDOW` e `WS_SYSMENU`), acompanhada pelo seu arquivo de testes `integracao_windows_test.py` com 100% de cobertura.
- **Definição Explícita de Título e Integração na `TelaDeAbertura`**: Definir explicitamente o título da janela (`self.setWindowTitle("Editor Aresta")`) e acionar a biblioteca de integração com o sistema operacional para qualificar a janela perante a barra de tarefas e o alternador de janelas (`Alt+Tab`).
- **Antecipação do Ícone Global da Aplicação**: Garantir a definição imediata do ícone da aplicação (`app.setWindowIcon(...)`) logo após a criação da instância do `QApplication` na função `main()`, assegurando consistência em qualquer diálogo anterior à janela de seleção.

## Capabilities

### New Capabilities

*(Nenhuma nova capacidade introduzida)*

### Modified Capabilities

- `editor-inicializacao`: Atualizar o requisito da `TelaDeAbertura` para exigir que a janela possua integração explícita com a barra de tarefas do sistema operacional Windows, exibindo o ícone e título oficiais da aplicação desde o momento de exibição inicial.

## Impact

- **Código afetado**: Novo módulo `editor/core/integracao_windows.py` (e `integracao_windows_test.py`), além de modificações em `editor/views/tela_de_abertura.py` e `editor/main.py`.
- **Princípios do Repositório**: Aderência estrita a `PRINCIPIOS.md` (Tudo em Português, Library-First, 100% de cobertura de testes, TDD Red-Green-Refactor, testes de integração em primeiro lugar e simplicidade anti-abstração).
- **APIs/Dependências**: Biblioteca padrão do Python (`ctypes`, `sys`) de forma condicional para o Windows. Sem dependências externas adicionais.
