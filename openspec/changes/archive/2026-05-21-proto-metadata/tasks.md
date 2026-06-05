## 1. Definição das Opções no Protobuf

- [x] 1.1 Adicionar em `FieldOptions` os campos: Enum `TipoConteudo`, `conteudo` (TipoConteudo, ID 50003), `mensagem` (string, ID 50004), e `conteudo_markdown` (bool, ID 50005) em `croqui.proto`.
- [x] 1.2 Adicionar em `MessageOptions` o campo: Enum `MensagemFormatoUi` e `mensagem_formato_ui` (MensagemFormatoUi, ID 50002) em `croqui.proto`.

## 2. Aplicação das Opções de Mensagem

- [x] 2.1 Identificar mensagens em `croqui.proto` que devem possuir o formato de UI "separado" e aplicar `[(aresta.mensagem_formato_ui) = "separado"]` (ex: `Pico`, `Grupo`, `Setor`, `Escalada`).
- [x] 2.2 Identificar mensagens em `croqui.proto` que devem possuir o formato de UI "oneof_conteudo" (ex: `ArquivoSetor`, `ArquivoGrupo`, `ArquivoMarkdown`) e aplicar a option apropriada.

## 3. Aplicação das Opções de Campo

- [x] 3.1 Revisar os campos em `croqui.proto` e adicionar a option `[(aresta.ui_label) = "..."]` nos casos em que o nome derivado não é intuitivo o suficiente (ex: `url_video_beta`, `chave_pix_manutencao`, `id_no_mapa`).
- [x] 3.2 Adicionar a option `[(aresta.conteudo) = "caminho"]` e o correspondente `[(aresta.mime_type) = "..."]` onde for aplicável.
- [x] 3.3 Marcar os campos de descrição com a option `[(aresta.conteudo_markdown) = true]`.

## 4. Validação e Compilação

- [x] 4.1 Garantir que o `croqui.proto` ainda compila normalmente executando as validações, caso haja algum passo de compilação ou checagem sintática do repositório para os protobufs.
- [x] 4.2 Adicionar teste de validação para garantir no máximo um campo `conteudo_markdown` por mensagem.
