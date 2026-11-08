## MODIFIED Requirements

### Requirement: Botão de ponte para o formato MAPA
O sistema MUST apresentar a mensagem identificada pela anotação `(aresta.mensagem_formato_na_ui) = MAPA` e os cartões `WidgetCardMapa` com botões de ação direta para abrir o mapa no Editor de Mapas (`"Abrir no Editor de Mapas"`) e para substituir a imagem do mapa (`"Substituir Imagem..."`), abstendo-se de expandir seus sub-campos ou sub-mensagens no formulário padrão.

#### Scenario: Visualizar mapa na árvore
- **WHEN** o usuário seleciona um nó associado ao formato `MAPA` no `WidgetEditorDados` ou visualiza um `WidgetCardMapa`
- **THEN** o editor exibe os botões `"Abrir no Editor de Mapas"` e `"Substituir Imagem..."` ao invés de listar todos os campos textuais para edição

#### Scenario: Ativação da ponte para o editor visual
- **WHEN** o usuário clica em `"Abrir no Editor de Mapas"`
- **THEN** o aplicativo ativa a aba do `WidgetEditorMapas` na `JanelaPrincipal` e foca no mesmo mapa que estava selecionado na árvore de dados

#### Scenario: Substituição de imagem do mapa direto pelo Editor de Dados
- **WHEN** o usuário clica em `"Substituir Imagem..."` no `WidgetCardMapa` ou no nó `MAPA` do `WidgetEditorDados` e confirma uma imagem no wizard unificado
- **THEN** o sistema substitui a imagem do mapa, atualiza `largura_mapa` e `altura_mapa` (e opcionalmente reescala proporcionalmente os POIs) em um único comando atômico (`CmdMacro`) na pilha de histórico e atualiza a miniatura e resolução exibidas no card

### Requirement: O usuário DEVE poder adicionar um mapa a partir da interface principal usando um novo Diálogo
O sistema SHALL interceptar o clique em `"Adicionar Item"` quando for do tipo `Mapa` e mostrar a interface do `DialogoAdicionarMapa` estruturada com duas abas (`"Importar Nova Imagem"` com suporte a recorte interativo e `"Imagens do Croqui"` com galeria pesquisável do disco e da memória RAM).

#### Scenario: Interceptar botão de Adicionar Mapa
- **WHEN** o usuário clica em `"Adicionar Item"` em uma lista repeated do tipo `Mapa` no `WidgetEditorDados`
- **THEN** o sistema exibe o `DialogoAdicionarMapa` com as abas `"Importar Nova Imagem"` e `"Imagens do Croqui"` em vez de criar o item diretamente

#### Scenario: Adição de mapa escolhendo imagem existente da galeria do croqui
- **WHEN** o usuário seleciona a aba `"Imagens do Croqui"` no `DialogoAdicionarMapa`, escolhe uma imagem existente em disco ou em memória RAM e confirma
- **THEN** o sistema cria o novo item `Mapa` apontando para o caminho e dimensões reais da imagem selecionada através da pilha de histórico (`QUndoStack`)
