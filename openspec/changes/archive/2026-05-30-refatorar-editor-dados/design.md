## Context

Atualmente, o Editor Aresta exibe uma representação 1:1 de cada campo do Protobuf `Croqui` na árvore de navegação do lado esquerdo. Quando o usuário seleciona um campo, apenas esse campo individual é exibido e pode ser editado na área do formulário à direita. Essa abordagem torna a edição muito granular, poluindo a visualização da árvore com campos primitivos e forçando o usuário a clicar constantemente para preencher dados correlacionados de uma mesma entidade (ex: um Pico ou um Setor).

## Goals / Non-Goals

**Goals:**
- Modificar o `ProtobufTreeModel` para expor apenas os nós correspondentes a mensagens que possuem as anotações `MensagemFormatoUi.SEPARADO` ou `MensagemFormatoUi.ONEOF_CONTEUDO`.
- Construir um formulário completo na área principal à direita contendo todos os campos pertencentes à mensagem selecionada.
- Suportar aninhamento recursivo direto no formulário para sub-mensagens marcadas como `MensagemFormatoUi.INLINE`.
- Prover botões de controle de presença de valor ("Adicionar", "Modificar", "Remover") para campos opcionais e repetidos.
- Annotar as mensagens estruturais principais (`Pico`, `Grupo`, `Setor`, `Escalada`) como `SEPARADO` no `croqui.proto`.

**Non-Goals:**
- Modificar outras abas do editor (Imagens, Mapas e Histórico).
- Alterar o fluxo de salvamento de arquivos físicos no disco.

## Decisions

1. **Reimplementação do ProtobufTreeModel:**
   - Em vez de construir nós para todos os campos do descritor (incluindo escalares), o modelo agora começará a partir da mensagem raiz `Croqui` e procurará recursivamente por seus descendentes diretos que possuam `mensagem_formato_ui == SEPARADO` ou `mensagem_formato_ui == ONEOF_CONTEUDO`.
   - Se um campo de mensagem não for um desses dois tipos, a busca recursiva desce por ele até encontrar sub-mensagens elegíveis (ex: navegando por `SetorOuGrupo` para encontrar `Setor`).
   - Para campos repetidos (ex: `picos`, `arquivos_markdown`), criaremos um nó agrupador intermediário ("expando") com o nome do campo. Sob esse nó agrupador, listaremos cada item correspondente da coleção individualmente e sequencialmente.

2. **Formulários Unificados na Direita (WidgetFormularioPadrao):**
   - O formulário será gerado dinamicamente iterando sobre `descriptor.fields` da mensagem selecionada.
   - Para cada campo, exibiremos um layout vertical/horizontal com:
     - Rótulo (Label): Usando `ui_label` ou convertendo o nome do campo.
     - Descrição: Lendo os comentários associados do arquivo `.proto` (via metadata do descriptor ou tooltip/label complementar).
     - Componente de Edição: Dependendo do tipo do campo (QLineEdit, QSpinBox, etc.).
     - Botões de Controle:
       - Se o campo não estiver setado (has_field == False): Mostra um botão "Adicionar".
       - Se o campo estiver setado: Mostra o editor e um botão "Remover".

3. **Renderização de Sub-mensagens INLINE:**
   - Mensagens anotadas com `MensagemFormatoUi.INLINE` (ex: `Coordenada`, `Patrocinador`) serão renderizadas diretamente dentro do formulário da mensagem pai.
   - O layout delas será envolvido em uma moldura/sub-layout delimitado por bordas bem definidas e visíveis, não margens.

4. **Anotações no croqui.proto:**
   - Modificaremos as mensagens `Pico`, `Grupo`, `Setor` e `Escalada` em `croqui.proto` para conter a opção `option (aresta.mensagem_formato_ui) = SEPARADO;`.

## Risks / Trade-offs

- **Risco:** Perda de reatividade ao adicionar/remover itens que afetem a árvore.
  - **Mitigação:** Certificar que o `ProtobufTreeModel` sinalize as mudanças no Qt (`beginResetModel`/`endResetModel` ou inserção de linhas) sempre que a estrutura interna de sub-mensagens `SEPARADO` sofrer adição ou remoção de nós.
