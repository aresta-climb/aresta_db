## ADDED Requirements

### Requirement: Botão de ponte para o formato MAPA
O sistema MUST apresentar a mensagem identificada pela anotação `(aresta.mensagem_formato_na_ui) = MAPA` através de um único botão de ação (Call To Action), abstendo-se de expandir seus sub-campos ou sub-mensagens no formulário padrão.

#### Scenario: Visualizar mapa na árvore
- **WHEN** o usuário seleciona um nó associado ao formato `MAPA` no WidgetEditorDados
- **THEN** o editor exibe o botão "Abrir no Editor de Mapas" ao invés de listar todos os campos textuais para edição

#### Scenario: Ativação da ponte para o editor visual
- **WHEN** o usuário clica em "Abrir no Editor de Mapas"
- **THEN** o aplicativo ativa a aba do `WidgetEditorMapas` na JanelaPrincipal e foca no mesmo mapa que estava selecionado na árvore de dados
