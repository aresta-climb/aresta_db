## Why

O editor de dados é o coração do Aresta Editor, permitindo que os autores modifiquem a estrutura do croqui (`croqui.proto`) através de uma interface rica, amigável e validada visualmente. Sem essa interface, a modificação exigiria a edição manual de arquivos textuais de forma complexa e propensa a erros, anulando as vantagens do aplicativo desktop.

## What Changes

- Implementação da "Página de Editor" (Editor de Dados) acessível a partir da toolbar lateral.
- Construção de uma visão de árvore (TreeView) no terço esquerdo da tela, similar a um File Explorer, para navegar hierarquicamente por toda a estrutura do Protobuf do croqui.
- Desenvolvimento da área principal de edição à direita, a qual carrega e renderiza dinamicamente um formulário adequado para visualizar e editar o item protobuf selecionado na árvore (strings, floats, repetições, etc).
- Integração profunda: Quando um campo de imagem ou um mapa for selecionado na árvore de dados, a área principal deve instanciar e abrir o "Editor de Imagens" ou o "Editor de Mapas", respectivamente.
- **Transparência de Arquivos (`Arquivo*`)**: O editor e a árvore devem tratar sub-mensagens do tipo `ArquivoSetor`, `ArquivoGrupo`, `ArquivoMarkdown` e `ArquivoExterno` de forma transparente. O usuário nunca deve ver a estrutura do `oneof` (caminho/conteudo). Em vez disso, a árvore e o formulário renderizam diretamente o sub-proto correspondente e, ao salvar, sempre utilizam a opção `caminho` (nunca `conteudo`).
- **UI Guiada por Protobuf**: Todo o texto exibido na interface do editor (títulos de campos, documentações de tooltip, descrições) deve ser extraído dinamicamente das definições e comentários dos arquivos `.proto`, ou de opções customizadas (field/message options), garantindo que a documentação na interface gráfica seja idêntica e definida diretamente no schema do Protobuf.

## Capabilities

### New Capabilities
- `editor-dados-arvore`: Funcionalidade de navegação e exibição em formato de árvore de todos os campos e sub-mensagens do protobuf.
- `editor-dados-formularios`: Renderização dinâmica de formulários na área principal com suporte a opções customizadas de representação baseadas em tipos (MIME types).

### Modified Capabilities
- `editor-area-principal`: Expandida para gerenciar e ancorar a nova view de Editor de Dados.
- `editor-imagens`: Agora precisa ser acionado dentro da área de edição do editor de dados ao se selecionar um nó associado a imagem.
- `editor-mapas`: Agora precisa ser acionado dentro da área de edição do editor de dados ao se selecionar um nó de mapa.

## Impact

- Mudança fundamental na arquitetura de UI do editor desktop.
- Integração necessária com ferramentas de serialização/deserialização do Google Protobuf e Python.
- Dependência direta dos componentes recém-criados `WidgetEditorImagens` e ferramentas de mapa para se integrarem em um contexto de aba ou frame único.
