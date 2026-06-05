## Context

O Aresta Editor atualmente gera formulários e visualizações para editar os dados de croqui baseado nas definições do `croqui.proto`. Para tornar o editor genérico e customizável, precisamos injetar opções nas mensagens e nos campos do protobuf. A equipe optou por usar custom options do Protobuf, estendendo `FieldOptions` e `MessageOptions`.

## Goals / Non-Goals

**Goals:**
- Definir as novas `FieldOptions` e `MessageOptions` no arquivo `croqui.proto`.
- Aplicar essas opções aos campos de forma que a UI possa consumir essas informações durante a execução.
- Garantir que as opções estejam corretas quanto à tipagem e numeração dos IDs de extensão.

**Non-Goals:**
- Implementar a lógica de leitura e processamento dessas opções no Aresta Editor (isso é escopo de desenvolvimento do próprio editor e não desta change do Protobuf).

## Decisions

1.  **Tipos das Field Options:**
    Como as *custom options* já foram introduzidas como extensão (`extend google.protobuf.FieldOptions`) no arquivo, adicionaremos as seguintes (além das 50001 e 50002 existentes):
    -   `enum TipoConteudo { CONTEUDO_INLINE = 0; CONTEUDO_CAMINHO = 1; }`
    -   `optional TipoConteudo conteudo = 50003;`
    -   `optional string mime_type = 50001;` (já existente, manteremos)
    -   `optional string ui_label = 50002;` (já existente, manteremos)
    -   `optional string mensagem = 50004;`
    -   `optional bool conteudo_markdown = 50005;`
2.  **Tipos das Message Options:**
    -   Adicionar à extensão existente `google.protobuf.MessageOptions`:
    -   `enum MensagemFormatoUi { MENSAGEM_FORMATO_UI_INLINE = 0; MENSAGEM_FORMATO_UI_SEPARADO = 1; MENSAGEM_FORMATO_UI_ONEOF_CONTEUDO = 2; }`
    -   `optional MensagemFormatoUi mensagem_formato_ui = 50002;`
3.  **Aplicação no `croqui.proto`:**
    -   Identificar campos não-óbvios e adicionar `[(aresta.ui_label) = "..."]`. Por exemplo, `url_google_maps`, `url_filiacao_associacao`, `chave_pix_manutencao`.

## Risks / Trade-offs

-   **Risco:** Usar IDs já reservados para outras opções em repositórios externos.
    -   **Mitigação:** Vamos usar IDs na faixa de 50000+ permitidos para projetos locais pelo padrão Protobuf.
