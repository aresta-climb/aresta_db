# splash-screen-draggable Specification

## Purpose
Atualizar a tela de abertura para exibir a identidade visual do Aresta Climb e permitir que o usuário arraste a janela.

## Requirements

### Requirement: Splash screen com arrasto
A tela de abertura do sistema SHALL permitir que o usuário arraste e mova a janela para diferentes posições na tela.

#### Scenario: Arrastar e soltar a janela
- **WHEN** o usuário clica com o botão esquerdo e segura no fundo da tela de abertura e move o mouse
- **THEN** a posição da janela deve se deslocar de acordo com a movimentação do ponteiro do mouse, sem afetar o funcionamento de outros controles interativos como botões

### Requirement: Identidade visual do Aresta Climb
A tela de abertura do sistema SHALL exibir o ícone correspondente à identidade visual do aplicativo móvel oficial.

#### Scenario: Visual atualizado
- **WHEN** a tela de abertura é renderizada
- **THEN** ela deve apresentar o ícone de logo oficial em vez do ícone genérico da montanha azul desenhado via código.
