## Context

Ao inicializar o Editor Aresta no Windows, o aplicativo exibe a `TelaDeAbertura` enquanto executa tarefas em segundo plano (verificação de sessão, sincronização de repositório e checagem de atualizações). Essa janela é construída com PySide6 utilizando `Qt.WindowType.FramelessWindowHint` e fundo translúcido para exibir um cartão moderno com bordas arredondadas.

No Windows, janelas sem moldura (`FramelessWindowHint`) são criadas nativamente pela camada de plataforma do Qt com estilo `WS_POPUP` sem `WS_CAPTION`. Por padrão da Shell do Windows, janelas popups puras não criam botões na barra de tarefas a menos que possuam o estilo estendido `WS_EX_APPWINDOW`. Além disso, o processo invoca `SetCurrentProcessExplicitAppUserModelID("aresta.editor.v1")`, o que desassocia o processo do ícone do executável binário e força o Windows a buscar o ícone exclusivamente através de uma janela ativa associada à barra de tarefas via mensagem `WM_GETICON`.

Como a `TelaDeAbertura` não se qualificava como janela de barra de tarefas, o botão da aplicação permanecia órfão com o ícone genérico padrão do Windows (retângulo branco com topo azul), até que a `TelaDeCarregamento` (que é um `QDialog` com `WS_CAPTION`) fosse aberta.

Em estrita conformidade com o documento `PRINCIPIOS.md`, este design adota a abordagem **Library-First**, desenvolvendo uma biblioteca autossuficiente, 100% em português brasileiro, com 100% de cobertura de testes unitários e foco no fluxo TDD (Red-Green-Refactor).

## Goals / Non-Goals

**Goals:**
- **Library-First**: Criar a biblioteca `editor/core/integracao_windows.py` com funções autossuficientes e testáveis de forma independente para configuração de janelas na barra de tarefas do Windows.
- **Tudo em Português**: Definir identificadores, variáveis, funções e documentação integralmente em português brasileiro (ex: `configurar_presenca_barra_de_tarefas`).
- **Presença e Ícone Imediatos**: Fazer com que a `TelaDeAbertura` exiba o ícone oficial da aplicação (`logo_app.png`) na barra de tarefas do Windows desde o primeiro milissegundo de sua exibição.
- **Identificação da Janela**: Definir o título da janela (`"Editor Aresta"`) para acessibilidade, alternador de tarefas (`Alt+Tab`) e tooltip da barra de tarefas.
- **100% de Cobertura de Testes**: Garantir cobertura completa de testes unitários e de integração nos novos módulos e classes ajustadas.

**Non-Goals:**
- Não criar molduras visuais nativas ou barras de título padrão do Windows sobre a `TelaDeAbertura` (a janela continua frameless e translúcida).
- Não alterar as telas subsequentes (`TelaDeCarregamento`, `JanelaPrincipal`), que já operam corretamente.
- Não introduzir dependências externas de terceiros; utilizar estritamente os módulos da biblioteca padrão do Python (`ctypes`, `sys`).

## Decisions

### Decisão 1: Criação da Biblioteca `editor/core/integracao_windows.py` (Library-First)
**Escolha:** Separar a lógica de baixo nível do sistema operacional em uma biblioteca independente do núcleo do editor, em vez de acoplar chamadas diretas de `ctypes` no interior do widget `TelaDeAbertura`.

Assinatura da função principal:
```python
def configurar_presenca_barra_de_tarefas(identificador_janela: int) -> bool:
    """
    Configura os estilos estendidos WS_EX_APPWINDOW e WS_SYSMENU no handle Win32 da janela
    para garantir que janelas sem moldura (frameless) sejam exibidas com ícone na barra de tarefas.
    
    Retorna True se os estilos foram aplicados com sucesso (ou em caso de no-op fora do Windows),
    ou False caso ocorra falha na chamada Win32.
    """
```
**Racional segundo `PRINCIPIOS.md`:**
- **Princípio II (Library-First)**: A lógica do sistema operacional é isolada, documentada e testável de maneira pura, sem necessidade de instanciar a interface gráfica complexa para validar o comportamento dos estilos.
- **Princípio VI (Simplicidade e Anti-Abstração)**: Código direto, funcional e declarativo, sem classes complexas ou camadas de abstração desnecessárias.

### Decisão 2: Estilos Win32 `WS_EX_APPWINDOW` e `WS_SYSMENU`
**Escolha:** Aplicar `WS_EX_APPWINDOW` (`0x00040000`) e `WS_SYSMENU` (`0x00080000`) sobre o handle da janela (`HWND`) obtido via `winId()`.
- `WS_EX_APPWINDOW`: Força a Shell do Windows a incluir a janela na barra de tarefas mesmo que ela seja do tipo popup sem bordas.
- `WS_SYSMENU`: Habilita o menu de contexto de janela na barra de tarefas (permitindo minimizar e fechar) sem introduzir elementos visuais de borda.

### Decisão 3: Definição Explícita de `setWindowTitle("Editor Aresta")`
**Escolha:** Chamar `self.setWindowTitle("Editor Aresta")` no construtor da `TelaDeAbertura`.
**Racional:** A Shell do Windows consulta `GetWindowTextW` para apresentar o nome do aplicativo no hover do botão e no alternador `Alt+Tab`. Sem essa definição, o Windows assume o nome do executável pai (`python`).

### Decisão 4: Antecipação do Ícone Global em `main()`
**Escolha:** Invocar `app.setWindowIcon(...)` imediatamente após instanciar `app = QApplication(sys.argv)` no ponto de entrada `main()`.
**Racional:** Previne qualquer estado intermediário onde caixas de diálogo preliminares (como aviso de instância única em execução) herdem o ícone padrão do Windows.

## Risks / Trade-offs

- **[Risco] Execução em ambientes de CI / Linux / macOS**
  → *Mitigação*: A função `configurar_presenca_barra_de_tarefas` verifica `sys.platform == "win32"` e opera como no-op seguro retornando `True` fora do Windows. O módulo de teste `integracao_windows_test.py` testa tanto a execução real quanto cenários simulados via mock para assegurar 100% de cobertura independente do sistema operacional da pipeline.
- **[Risco] Chamada prematura de `winId()` no PySide6**
  → *Mitigação*: Invocar `winId()` em um `QWidget` de nível superior instancia o `HWND` Win32 de forma segura sem forçar a exibição antecipada da janela. Os testes empíricos confirmam a persistência intacta dos estilos após o método `show()`.
