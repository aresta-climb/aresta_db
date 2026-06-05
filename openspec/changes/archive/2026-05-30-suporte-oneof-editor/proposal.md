## Why

Esta alteração é necessária para simplificar o editor de croquis, abstraindo os detalhes de implementação das mensagens wrapper contendo `oneof`. Atualmente, a árvore exibe e exige que o usuário interaja com elementos como `ArquivoSetor` ou `SetorOuGrupo` explicitamente. Com esta mudança, o editor irá esconder essas mensagens "wrapper" e exibir diretamente a mensagem aninhada selecionada, tornando a árvore de navegação e os formulários mais limpos e intuitivos. 

Além disso, para melhorar a experiência de edição textual de croquis, é necessário introduzir um editor de Markdown rico integrado side-by-side, permitindo a edição confortável de descrições e seções textuais salvas em arquivos externos `.md`. O editor deve manter a sincronia entre a UI (onde o nome do arquivo externo é editável) e os arquivos físicos no disco (com YAML frontmatter e corpo de texto), e garantir que a renderização de imagens locais na pré-visualização seja ajustada automaticamente ao viewport do painel de visualização.

## What Changes

- **Abstração automática de Oneofs**: Mensagens do tipo `ONEOF` (identificadas pela mensagem option `(aresta.mensagem_formato_na_ui) = ONEOF`) serão invisíveis no editor. Em seu lugar, o editor exibirá e manipulará diretamente o campo/mensagem aninhada ativa.
- **Suporte a `oneof_default`**: Adição da opção de campo `[(aresta.oneof_default) = true]`. Ao criar uma nova instância de uma mensagem que contenha um `oneof`, se houver um campo marcado como `oneof_default`, ele será selecionado e criado automaticamente. Caso contrário, a UI solicitará ao usuário que escolha qual opção do `oneof` deseja criar.
- **Suporte a `titulo_na_ui`**: Adição da opção de campo `[(aresta.titulo_na_ui) = true]`. Permite marcar um campo de texto de uma sub-mensagem como o título representativo daquela mensagem na árvore de navegação do editor.
- **Transparência de Wrappers de Arquivos**: O editor esconderá a existência física de wrappers como `ArquivoSetor`, `ArquivoGrupo`, `ArquivoMarkdown` no formulário e árvore de dados, mas salvará as informações em arquivos externos correspondentes conforme especificado.
- **Carregamento e Escrita de Arquivos Externos (.md)**: Carregamento recursivo no início de arquivos `.md` (decodificando YAML frontmatter para propriedades e markdown body para descrição/conteúdo). Salvamento isolado por meio de cópia profunda do croqui, atualizando referências, gerando arquivos físicos no formato de frontmatter + markdown, e apagando arquivos antigos renomeados.
- **Edição de Nome de Arquivo na UI**: Exibição de um `QLineEdit` ("Nome do arquivo:") no topo do formulário para itens mantidos em arquivos separados. Geração automática de nomes de arquivo padrão e únicos ao inserir novos itens.
- **Editor de Markdown Rico (Split-Pane)**: Painel side-by-side com um `QTextEdit` para edição em texto puro e um `AutoScalingTextBrowser` que renderiza o markdown formatado em tempo real, ocultando o frontmatter, resolvendo caminhos de imagens locais através do `baseUrl` e redimensionando as imagens proporcionalmente para caber no viewport sem gerar rolagem horizontal.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `editor-dados-arvore`: Modificado para suportar o comportamento transparente para qualquer mensagem do tipo `ONEOF`, resolvendo e exibindo a mensagem aninhada ativa automaticamente tanto na árvore quanto nos formulários, e tratando a criação de novos nós contendo `oneof` respeitando a opção `oneof_default`.
- `editor-dados-formularios`: Modificado para exibir a edição de nome de arquivo externo no topo, e renderizar o componente split-pane (`WidgetEditorMarkdown`) para campos de markdown com preview renderizado em tempo real e auto-scaling dinâmico de imagens.
- `editor-area-principal`: Modificado para ler e salvar os arquivos `.md` externos de forma recursiva, mantendo estabilidade de referências na memória dos objetos e gerenciando a exclusão de arquivos antigos renomeados por meio de salvamento atomizado.
- `protobuf-editor-metadata`: Modificado para incluir suporte formal e comportamento para as field options `oneof_default` e `titulo_na_ui`.

## Impact

- `editor/core/protobuf_tree_model.py`: Atualizado para resolver os wrappers `ONEOF` de forma dinâmica e usar `titulo_na_ui` para rotular nós na árvore.
- `editor/views/widget_editor_dados.py` / `editor/views/protobuf_widget_factory.py`: Atualizados para gerenciar formulários, comboboxes de seleção de oneof e inicialização de valores respeitando `oneof_default`, o comportamento de transparência para mensagens do tipo `ONEOF`, renderização do campo de nome do arquivo, e renderização split-pane para markdown.
- `editor/views/area_principal.py`: Atualizado para gerenciar o carregamento de arquivos `.md` externos, rastreamento de nomes de arquivo em RAM via dicionários, salvamento atomizado (deep copy), e exclusão física de arquivos renomeados no disco.
