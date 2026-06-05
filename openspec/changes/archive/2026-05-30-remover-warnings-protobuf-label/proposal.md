## Why

Os testes do Aresta geram muitos avisos de obsolescência (`DeprecationWarning`) devido ao uso do atributo `FieldDescriptor.label` na biblioteca do Python `protobuf`. Esses warnings poluem a saída dos testes e dificultam a visualização de outros avisos ou erros relevantes. Esta alteração resolve esses warnings utilizando as propriedades modernas recomendadas.

## What Changes

- Substituição de `field.label == FieldDescriptor.LABEL_REPEATED` (e equivalentes) pelo uso direto da propriedade booleana `field.is_repeated` em todos os locais onde os descritores do Protobuf são inspecionados para identificar campos repetidos.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capacidade necessária. -->

### Modified Capabilities
- `editor-dados-arvore`: Garantia de compatibilidade do parser e modelador da árvore com runtimes modernos do Protobuf que depreciaram o campo `.label`.

## Impact

- **Código Afetado**: 
  - O modelo de dados da árvore do editor em [protobuf_tree_model.py](file:///c:/Renato/Devel/aresta/aresta_db/editor/core/protobuf_tree_model.py)
  - Os widgets de renderização dinâmica de formulários em [widget_editor_dados.py](file:///c:/Renato/Devel/aresta/aresta_db/editor/views/widget_editor_dados.py)
- **APIs/Dependências**: Sem impactos externos. Trata-se de uma atualização preventiva de compatibilidade com a biblioteca `protobuf`.
