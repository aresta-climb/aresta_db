## ADDED Requirements

### Requirement: O usuário DEVE poder adicionar um mapa a partir da interface principal usando um novo Diálogo

O sistema DEVE interceptar o clique em "Adicionar Item" quando for do tipo `Mapa` e mostrar a interface do `DialogoAdicionarMapa`.

#### Scenario: Interceptar botão de Adicionar Mapa
- **WHEN** o usuário clica em "Adicionar Item" em uma lista repeated do tipo `Mapa` no `WidgetEditorDados`
- **THEN** o sistema exibe o `DialogoAdicionarMapa` invés de criar o item diretamente.

### Requirement: O diálogo DEVE permitir o preview da imagem
O diálogo DEVE conter uma área de clique/drag-and-drop para o usuário escolher o arquivo da imagem. E após selecionado, exibir o preview.

#### Scenario: Visualizar imagem antes de confirmar
- **WHEN** o usuário arrasta uma imagem para a área do diálogo ou a seleciona através do file explorer
- **THEN** o diálogo atualiza a área com um *preview* da imagem para confirmação visual do usuário.

### Requirement: O diálogo DEVE sugerir o nome correto do arquivo e impedir sobrescrita indevida
A sugestão DEVE seguir a convenção de nomenclatura do projeto baseado nos pais do nó atual. O arquivo NÃO PODE ser sobrescrito acidentalmente.

#### Scenario: Nome gerado é único
- **WHEN** o usuário seleciona uma imagem
- **THEN** o campo "Nome de Arquivo" do diálogo mostra `grupo_<nome_grupo>_setor_<nome_setor>_p<numero_mapas_existentes>.webp`.

#### Scenario: Tentativa de usar nome de arquivo que já existe
- **WHEN** o usuário tenta confirmar (OK) no diálogo e o nome do arquivo já existe na pasta `imagens/`
- **THEN** o sistema exibe um alerta de erro e não permite confirmar, exigindo a edição manual do nome do arquivo.

### Requirement: A imagem DEVE ser comprimida em WebP e o histórico de ações tratado por um QUndoCommand
Ao confirmar, a imagem será comprimida, guardada na memória do `QUndoCommand`, e só então o `redo()` será disparado escrevendo-a e adicionando os dados no `CroquiModel`. O `undo()` removerá o arquivo local.

#### Scenario: Criação efetiva e Desfazer
- **WHEN** o usuário confirma o diálogo de um novo mapa
- **THEN** a imagem é adequadamente redimensionada (área <= 2048*2048 pixels) e convertida (WebP-85), o arquivo é escrito no disco na pasta respectiva e o mapa é criado no protobuf.
- **WHEN** o usuário aciona o recurso de "Desfazer"
- **THEN** o item é apagado do protobuf e o arquivo físico de imagem gerado é removido do sistema de arquivos.
