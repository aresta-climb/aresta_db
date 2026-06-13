## MODIFIED Requirements

### Requirement: Opções customizadas de mensagem para formato UI
O sistema SHALL disponibilizar option de mensagem (extensão de `MessageOptions`) para ditar como a árvore do editor apresentará a mensagem: `mensagem_formato_na_ui` com valores do enum `MensagemFormatoUi.Enum`, incluindo agora o valor `MAPA`.

#### Scenario: UI Separada
- **WHEN** uma mensagem tem a option `[(aresta.mensagem_formato_na_ui) = SEPARADO]`
- **THEN** a UI deve exibi-la como um item separado na árvore, ao invés de mostrá-la inline.

#### Scenario: UI com Abstração Oneof
- **WHEN** uma mensagem tem a option `[(aresta.mensagem_formato_na_ui) = ONEOF]`
- **THEN** a UI deve ocultá-la na árvore e exibir diretamente seu campo ativo ou sub-mensagem.

#### Scenario: UI como Botão de Mapa
- **WHEN** uma mensagem tem a option `[(aresta.mensagem_formato_na_ui) = MAPA]`
- **THEN** a UI do formulário padrão deve ser suprimida, exibindo-se em vez disso um botão que direciona o usuário para a interface visual especializada (Editor de Mapas).
