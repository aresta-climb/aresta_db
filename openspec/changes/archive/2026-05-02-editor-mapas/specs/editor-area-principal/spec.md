## MODIFIED Requirements

### Requirement: Barra de Ferramentas Lateral (Side Toolbar)
A Side Toolbar SHALL conter ícones premium (via QtAwesome) dispostos verticalmente na lateral esquerda, permitindo alternar entre as visões: Dados, Imagens, Mapas e Histórico.
- **Dimensões**: SHALL possuir 82px de largura total.
- **Botões**: SHALL possuir margens de 6px em todos os lados.

#### Scenario: Seleção de visão na barra lateral
- **WHEN** o usuário clica no ícone de "Mapas" na barra lateral
- **THEN** o conteúdo da área central SHALL ser atualizado para exibir o editor de mapas integrado, permitindo a edição visual dos POIs dos mapas do croqui atual.
