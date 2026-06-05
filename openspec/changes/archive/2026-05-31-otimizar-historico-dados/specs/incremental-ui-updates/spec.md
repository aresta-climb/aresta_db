## ADDED Requirements

### Requirement: Atualização Incremental de Valores Primitivos
O sistema SHALL atualizar os valores textuais, numéricos ou booleanos dos campos dinâmicos visualmente de forma estrita, sem recarregar o formulário global, reativo aos eventos de histórico (Undo/Redo).

#### Scenario: Undo de alteração de texto
- **WHEN** o usuário desfaz um comando de alteração de campo primitivo (ex: texto)
- **THEN** o formulário não deve recarregar, apenas o widget específico reverte seu conteúdo
- **THEN** o widget específico solicita e adquire o foco do teclado para continuidade da edição

### Requirement: Atualização Incremental Estrutural para Listas e Polimorfismo
O sistema SHALL processar a inserção e remoção de itens dentro de campos `repeated` ou de seleção em `oneof` manipulando apenas os sub-layouts afetados.

#### Scenario: Redo de adição em campo repeated
- **WHEN** o usuário aciona o refazer (redo) de uma ação que inseriu um novo elemento na coleção `repeated`
- **THEN** o widget de container daquela coleção instancia e injeta o layout do novo item na posição correta
- **THEN** o estado de rolagem (scroll) do formulário é preservado e os campos vizinhos permanecem intactos
