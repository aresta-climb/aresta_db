## 1. Modelo de Dados da Árvore

- [x] 1.1 Criar a classe `ProtobufTreeModel` herdando de `QAbstractItemModel` para mapeamento lazy-load.
- [x] 1.2 Implementar métodos fundamentais (`index`, `parent`, `rowCount`, `columnCount`, `data`) percorrendo iterativamente a estrutura de mensagens do Protobuf.
- [x] 1.3 Adicionar interceptação para os protos `Arquivo*` (`ArquivoSetor`, `ArquivoGrupo`, `ArquivoMarkdown`, `ArquivoExterno`), ignorando o nível do `oneof` (caminho/conteudo) e retornando diretamente o sub-proto na estrutura da árvore.
- [x] 1.4 Escrever testes unitários para garantir que o modelo da árvore mapeia campos simples e aninhados sem perdas de índices e que os wrappers de arquivos são resolvidos de forma transparente.

## 2. Formulários Dinâmicos

- [x] 2.1 Implementar sistema de metaprogramação (Fábrica de Widgets) que analisa `FieldDescriptor` para retornar `QLineEdit`, `QSpinBox` ou `QCheckBox` correspondentes ao tipo primitivo.
- [x] 2.2 Adicionar lógica de extração de comentários (usando `GetSourceLocation()` ou `source_code_info`) para popular tooltips e textos de ajuda (description) automaticamente, sem texto "hardcoded".
- [x] 2.3 Adicionar lógica que leia o nome do campo ou opções de field/message customizadas (`(ui_label)` e `(mime_type)` no `croqui.proto`) para definir os rótulos (labels) dos componentes no editor e na árvore.
- [x] 2.4 Criar widget especializado e reutilizável para renderizar campos `repeated` do protobuf (listas com controles independentes de + e -).
- [x] 2.5 Escrever testes unitários validando a geração dos widgets dinâmicos com dados iniciais populados, com comportamentos vazios (defaults), e verificando a presença das descrições extraídas dos `.proto`.

## 3. Interface Principal de Dados e Roteamento

- [x] 3.1 Construir a estrutura macro de `WidgetEditorDados`, instanciando a `QTreeView` à esquerda e um `QStackedWidget` à direita.
- [x] 3.2 Implementar listener de seleção da árvore que decide se a página ativa no `QStackedWidget` será o Formulário Padrão, o `WidgetEditorImagens` ou o `WidgetEditorMapas` com base nos `mime_types` ou características do campo.
- [x] 3.3 Escrever testes de integração avaliando o sinal emitido pelo `QTreeView` e garantindo que o painel da direita carrega a janela/view correta.

## 4. Integração Final

- [x] 4.1 Acoplar o `WidgetEditorDados` no contexto principal (`WidgetAreaPrincipal` ou similar) quando o usuário seleciona o ícone "Dados" na `Side Toolbar`.
- [x] 4.2 Garantir que na lógica de salvamento (`salvar_croqui`), qualquer wrapper `Arquivo*` modificado utilize exclusivamente a configuração `caminho`, gravando o conteúdo em um arquivo separado (.yaml ou .md).
- [x] 4.3 Rodar fluxo completo (Testes E2E via automação PyTest) de abertura, navegação do croqui carregado, expansão de um nó (incluindo testes com `ArquivoSetor`), modificação, e persistência transparente.
