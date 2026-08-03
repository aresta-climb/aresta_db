## Why

Atualmente, não existe uma maneira declarativa de definir como cada campo do protobuf `croqui.proto` deve ser apresentado no Editor Aresta (como labels de interface, tipos de conteúdo MIME, etc.). Esta mudança adicionará metadados via custom field/message options no protobuf, permitindo que a UI de edição de croquis seja gerada ou adaptada automaticamente de acordo com as especificações de cada campo.

## What Changes

- Adiciona a option `ui_label` para personalizar o nome do campo exibido no aplicativo Editor Aresta.
- Adiciona a option `conteudo` (enum: 'caminho' ou 'inline') para especificar onde o conteúdo de bytes ou string reside.
- Adiciona a option `mime_type` para tipar os dados (ex: `text/markdown`, `text/markdown-yaml`, `application/protobuf`, `text/protobuf`).
- Adiciona a option `mensagem` que define o tipo da mensagem para dados seralizados (como text/markdown-yaml ou text/protobuf).
- Adiciona a option `conteudo_markdown` (booleano) indicando qual campo conterá o conteúdo em texto quando usando `text/markdown-yaml`.
- Adiciona a message option `mensagem_formato_ui` (enum: 'inline', 'separado', 'oneof_conteudo') para definir como mensagens complexas são tratadas na árvore do editor.
- Atualiza o arquivo `croqui.proto` aplicando estas opções, especialmente `ui_label`, onde o nome padrão (capitalizado e com espaços) não é o mais amigável ou óbvio para o usuário final.

## Capabilities

### New Capabilities
- `protobuf-editor-metadata`: Define como metadados adicionais de UI e dados (MIME types, renderização de árvores) são injetados nos arquivos `.proto` e como eles devem ser interpretados pelo sistema de edição para gerar formulários apropriados.

### Modified Capabilities

## Impact

- `aresta_api/proto/croqui.proto` será alterado para definir e utilizar as novas opções do protobuf.
- O Editor Aresta deverá ser capaz de ler essas extensões (options) para gerar a UI.
