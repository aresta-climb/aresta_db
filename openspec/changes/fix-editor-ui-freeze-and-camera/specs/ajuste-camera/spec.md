## ADDED Requirements

### Requirement: Exibição correta da câmera no mapa
O sistema SHALL exibir o retângulo de ajuste 9:16 (`ItemCameraOverlay`) na cena ativa toda vez que o modo de câmera for iniciado, garantindo visibilidade e dimensões válidas.

#### Scenario: Ativando modo de câmera no painel
- **WHEN** o usuário aciona o botão de câmera para um ponto de interesse no painel de referências
- **THEN** o overlay de ajuste é posicionado no mapa com largura (`width`) e altura (`height`) sempre maiores que zero, e visível (`isVisible() == True`).

#### Scenario: Injeção na cena
- **WHEN** a rotina de iniciação do modo de câmera não encontra um overlay preexistente ou este não está vinculado à cena
- **THEN** o `ItemCameraOverlay` deve ser adicionado explicitamente à cena (`scene().addItem()`) no tempo exato, garantindo seu Z-Value para não ser encoberto pelo croqui de fundo.
