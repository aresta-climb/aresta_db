# Design Técnico: Prevenção de Injeção de Dark Mode e Consistência de Contraste

## Contexto

O Aresta Editor utiliza PySide6 / Qt 6.11. No Windows 10 e 11, o Qt integra-se com a API de temas do Windows via QPA `qwindows`. Ao detectar que o usuário selecionou o modo escuro nas configurações do sistema operacional, o Qt reconfigura a `QPalette` do aplicativo para cores escuras de fundo e claras de texto.
No entanto, estilos locais (como na `TelaDeCarregamento`) forçam fundos claros (`#ffffff`, `#f8f9fa`) sem declarar a propriedade `color`, resultando em botões e títulos com texto branco sobre fundo branco. Além disso, caixas de diálogo filhas (como `QInputDialog`) herdam seletores não-escopados de `QPushButton`.

## Objetivos e Não-Objetivos

**Objetivos:**
- Garantir que em qualquer máquina com Windows em Dark Mode, a aplicação apresente a interface em tema claro com alto contraste e legibilidade impecável (conforme o esperado).
- Centralizar a configuração de paleta clara e política de tema no módulo `editor/views/estilo.py`.
- Ajustar os QSS locais para que botões e contêineres declarem `color` explicitamente sempre que definirem `background-color`.
- Escopar os estilos da `TelaDeCarregamento` para que botões genéricos de janelas filhas/diálogos não herdem estilos inadequados.
- Escrever testes automatizados (TDD) para garantir que a paleta e os componentes mantenham texto e contraste válidos mesmo sob tentativa de forçamento de modo escuro.

**Não-Objetivos:**
- Criar um tema escuro completo para o Aresta Editor nesta etapa (isso exigiria redesign visual de componentes, croquis e mapas, e será tratado em proposta futura).

## Decisões

### Decisão 1: Configuração antecipada de `QT_QPA_PLATFORM="windows:darkmode=0"`
- **Motivação**: O plugin de plataforma do Qt no Windows (`qwindows`) lê a opção `darkmode` no momento em que a plataforma é inicializada (ao instanciar `QApplication`). Com `darkmode=0`, o Qt desativa a integração nativa com o Windows Immersive Dark Mode, mantendo a moldura da janela clara e não aplicando a paleta escura do Windows.
- **Alternativa considerada**: Apenas alterar a `QPalette` manualmente via código. *Rejeitada como solução isolada*, pois não impede que o Windows DWM pinte a barra de título da janela de preto ou aplique métricas/cores escuras em menus nativos.

### Decisão 2: Forçamento explícito de `app.styleHints().setColorScheme(Qt.ColorScheme.Light)`
- **Motivação**: No Qt 6.5+, `styleHints().setColorScheme(Qt.ColorScheme.Light)` instrui formalmente o framework a adotar o esquema claro em todas as plataformas (Windows, Linux, macOS), alinhando paletas de widgets nativos.
- **Implementação**: Encapsulado em `editor/views/estilo.py:configurar_tema_claro_aplicacao(app: QApplication)`.

### Decisão 3: Escopamento e Higiene de QSS em `TelaDeCarregamento`
- **Motivação**: Em vez de `QPushButton { ... }` solto na folha de estilos do diálogo (que vaza para qualquer diálogo filho como `QInputDialog`), escopar os botões principais de ação com `#grupo_acoes QPushButton`, e definir explicitamente `color: #212529` para garantir que o texto seja sempre escuro sobre fundo claro.

## Riscos e Mitigações

- **[Risco]** Usuários rodando em Linux/macOS com modo escuro poderiam ter problemas similares se apenas o Windows fosse tratado.
  $\rightarrow$ **Mitigação**: O uso de `setColorScheme(Qt.ColorScheme.Light)` cobre todas as plataformas do Qt 6.5+, além do tratamento específico `windows:darkmode=0`.
- **[Risco]** Testes de UI podem falhar se tentarem instanciar múltiplos `QApplication`.
  $\rightarrow$ **Mitigação**: Os testes verificarão se `QApplication.instance()` já existe e validarão a configuração do `styleHints()` e o contraste das folhas de estilo.
