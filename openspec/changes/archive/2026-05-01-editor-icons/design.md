## Context

O Aresta Editor busca uma estética premium. Os ícones atuais são simplórios e não transmitem a qualidade desejada. A biblioteca `QtAwesome` é o padrão de mercado para aplicações PyQt/PySide que necessitam de ícones vetoriais modernos e customizáveis.

## Goals / Non-Goals

**Goals:**
- Adicionar `qtawesome` como dependência central da interface.
- Centralizar a definição de ícones em um único local para facilitar a manutenção e consistência.
- Aplicar o novo sistema de ícones em todas as barras de ferramentas da Janela Principal.

**Non-Goals:**
- Alterar a lógica funcional dos botões.
- Implementar um sistema de temas completo (apenas a base para ícones).

## Decisions

### 1. Centralização com `editor.views.estilo.Icones`
Criaremos uma classe utilitária (ou módulo) para gerenciar a criação de ícones.
- **Rationale**: Evitar que strings como `"fa5s.save"` fiquem espalhadas pelo código. Permite alterar o estilo de todos os ícones (cor, tamanho) em um único lugar.
- **Alternatives**: Chamar `qtawesome.icon()` diretamente em cada widget. Rejeitado por dificultar a manutenção visual.

### 2. Escolha do Conjunto: FontAwesome 5 Solid (`fa5s`)
- **Rationale**: Oferece a melhor cobertura de ícones de interface (UI) com um visual consistente e moderno.

### 3. Paleta de Cores e Estilização
- **Normal**: Cinza Grafite (`#454545`).
- **Destaque (Active/Hover)**: Azul Aresta (`#2b579a`).
- **Logo (Marca)**: Verde Musgo (`#556b2f`) com opacidade de 0.7 para distinguir de botões.
- **Unidades**: Uso obrigatório de `pt` (points) em vez de `px` para evitar erros de PointSize no Windows High-DPI.
- **Rationale**: Cores sóbrias e profissionais que reforçam a marca.

### 4. Grid Pixel-Perfect
- **Margens**: 6px constantes em todos os lados (L/R/T/B) e entre botões.
- **Largura Lateral**: 82px (70px botão + 12px margens).
- **Alinhamento Superior**: Espaçador inicial de 63px para alinhar o separador vertical com a borda da barra lateral.

## Risks / Trade-offs

- **[Risk] Compatibilidade com PyInstaller** → **Mitigation**: O `qtawesome` geralmente funciona bem, mas o script de build (`editor/build.py`) deve ser verificado para garantir que as fontes `.ttf` empacotadas pela biblioteca sejam incluídas no executável final.
- **[Trade-off] Dependência Adicional** → Aceitamos adicionar uma dependência de ~1MB para ganhar em qualidade visual e agilidade de desenvolvimento.
