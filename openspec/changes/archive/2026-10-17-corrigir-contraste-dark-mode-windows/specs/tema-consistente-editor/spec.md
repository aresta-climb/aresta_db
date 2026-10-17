## ADDED Requirements

### Requirement: O aplicativo deve forçar o tema claro independentemente do tema do sistema operacional
O sistema DEVE garantir que o ambiente Qt e a aplicação executem estritamente sob o esquema de cores claro, desativando a injeção nativa de tema escuro no Windows e forçando o esquema `ColorScheme.Light`.

#### Scenario: Inicialização no Windows com Dark Mode ativado
- **WHEN** o aplicativo for inicializado em um ambiente onde o Windows ou o sistema operacional possui modo escuro ativado
- **THEN** a variável `QT_QPA_PLATFORM` com `windows:darkmode=0` e o `colorScheme` do `QStyleHints` devem estar definidos como `Light`, assegurando que a paleta padrão de textos permaneça escura (`#000000`) e fundos padrão permaneçam claros.

### Requirement: Botões e agrupadores na tela de carregamento devem possuir contraste legível explícito
A `TelaDeCarregamento` DEVE especificar explicitamente a cor do texto (`color`) em todas as suas regras de folha de estilo (QSS) que definem cor de fundo (`background-color`), garantindo contraste legível mínimo mesmo sob paletas não convencionais.

#### Scenario: Renderização dos botões de ação na tela de carregamento
- **WHEN** a `TelaDeCarregamento` for exibida
- **THEN** os botões de ação principal ("Novo croqui", "Importar croqui experimental", "Editar croqui oficial") devem renderizar texto escuro legível sobre seus fundos claros, e os estilos de botão não devem vazar para janelas de diálogo internas.
