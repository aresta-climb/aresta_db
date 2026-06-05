# Design: Notificação Discreta de Salvamento

## Context
O editor atualmente utiliza `QMessageBox` para confirmar o salvamento. Isso é obstrutivo e desnecessário para uma ação frequente e esperada de sucesso.

## Goals / Non-Goals

**Goals:**
- Implementar um sistema de feedback visual não obstrutivo.
- Melhorar a fluidez do uso do editor, especialmente com auto-salvamento ativo.

**Non-Goals:**
- Não substituir mensagens de erro críticas que exigem atenção imediata (estas devem continuar usando `QMessageBox`).
- Não implementar um sistema complexo de fila de notificações (uma notificação por vez é suficiente).

## Decisions

### 1. Widget Customizado `NotificacaoToast`
Criar um widget `NotificacaoToast` em `editor/views/notificacao.py`.
- **Estilo**: Fundo escuro semi-transparente, bordas arredondadas, ícone de check verde e texto branco.
- **Posicionamento**: O widget será filho da `JanelaPrincipal` e se posicionará no canto inferior direito usando coordenadas relativas.

### 2. Animação e Ciclo de Vida
- **Exibição**: O widget será criado e exibido instantaneamente.
- **Timeout**: Um `QTimer` de 3000ms iniciará após a exibição.
- **Fade-out**: Ao final do timer, um `QPropertyAnimation` (na propriedade `windowOpacity` ou usando efeitos de opacidade) fará a transição suave para invisível.
- **Destruição**: O widget será destruído automaticamente (`setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)`) após a animação.

### 3. Integração na Janela Principal
A `JanelaPrincipal` terá um método auxiliar `exibir_notificacao(mensagem, sucesso=True)` que instanciará o toast. O método `salvar_croqui` será atualizado para chamar esta função em vez de `QMessageBox.information`.

## Risks / Trade-offs
- **Sobreposição**: O toast pode cobrir algum elemento importante da UI se não for bem posicionado. 
    - *Mitigação*: Posicionamento fixo com margem (ex: 20px de distância das bordas).
- **Z-Order**: Garantir que o toast apareça acima de outros widgets.
    - *Mitigação*: Usar `raise_()` e garantir que o parent seja a janela principal.
