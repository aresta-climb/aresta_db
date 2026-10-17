# Proposta: Corrigir Contraste do Editor no Windows Dark Mode

## Por que

Quando o Windows está configurado em Modo Escuro (*Dark Mode*), o Qt 6.5+ detecta nativamente a preferência do sistema e altera a `QPalette` para cores escuras de fundo e claras de texto. Como diversas partes da interface gráfica do Aresta Editor (como a `TelaDeCarregamento`, caixas de diálogo nativas e grupos) possuem folhas de estilo QSS parciais com fundos claros (`#ffffff`, `#f8f9fa`) sem definir a cor do texto (`color`), o texto dos botões e títulos é renderizado em branco sobre fundo branco, tornando a interface completamente ilegível.

Como a identidade visual atual do Editor foi inteiramente projetada para tema claro, é imperativo garantir a imunidade contra a injeção indesejada de paletas escuras do SO e assegurar contraste legível através de testes automatizados (TDD), prevenindo regressões visuais até que um Modo Escuro oficial seja planejado.

## O que muda

- **Forçamento de Tema Claro no Qt**: Configuração da variável de ambiente de plataforma `QT_QPA_PLATFORM="windows:darkmode=0"` e chamada explícita a `app.styleHints().setColorScheme(Qt.ColorScheme.Light)` na inicialização da aplicação (`editor/main.py`).
- **Saneamento e Qualificação de QSS**:
  - Definição explícita de `color` em todos os elementos com fundo claro em `TelaDeCarregamento`.
  - Escopamento dos seletores de botão (`#grupo_acoes QPushButton`) para evitar vazamento de estilos globais para diálogos filhos como `QInputDialog`.
- **Higiene de Contraste Centralizada**: Criação de utilitário em `editor/views/estilo.py` para configuração de paleta clara padrão do aplicativo (`configurar_tema_claro_aplicacao(app)`).
- **Testes Automatizados (TDD)**: Testes de unidade e integração garantindo que a aplicação e os diálogos mantenham contraste adequado e paleta clara mesmo se o ambiente solicitar modo escuro.

## Capacidades

### Novas Capacidades
- `tema-consistente-editor`: Garante consistência visual e contraste legível em tema claro no editor, independentemente das configurações de tema do sistema operacional hospedeiro.

### Capacidades Modificadas
<!-- Nenhuma capacidade existente teve seus requisitos de negócio alterados. -->

## Impacto

- `editor/main.py`: Inicialização do Qt e chamada de configuração de tema claro.
- `editor/views/estilo.py`: Função utilitária para aplicar e padronizar o esquema claro do aplicativo.
- `editor/legacy_views/tela_de_carregamento.py`: Folhas de estilo corrigidas com cores explícitas e seletores escopados.
- Testes automatizados adicionados para verificar contraste e prevenção de regressão.
