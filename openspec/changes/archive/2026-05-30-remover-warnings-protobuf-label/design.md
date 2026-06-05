## Context

Atualmente, o pytest acusa 284 warnings do tipo `DeprecationWarning: label() is deprecated. Use is_required() or is_repeated() instead.` devido ao uso do atributo `label` em objetos `FieldDescriptor` da biblioteca do Protobuf. Este documento de design descreve a estratégia simples para substituir essas chamadas pela propriedade moderna `.is_repeated`.

## Goals / Non-Goals

**Goals:**
- Eliminar todos os deprecation warnings relacionados a `FieldDescriptor.label` da suite de testes.
- Utilizar a propriedade moderna `is_repeated` integrada de forma nativa pela biblioteca `protobuf`.
- Garantir que o comportamento e o funcionamento do editor permaneçam 100% inalterados.

**Non-Goals:**
- Não atualizar nem alterar os arquivos gerados automaticamente pelo compilador protobuf (`croqui_pb2.py`).
- Não reescrever nem refatorar a lógica estrutural da árvore do editor ou do formulário dinâmico além do ponto necessário para sanar os warnings.

## Decisions

- **Decisão**: Substituir diretamente as verificações de `field.label == FieldDescriptor.LABEL_REPEATED` (e equivalentes) pelo uso da propriedade `field.is_repeated`.
  - **Alternativa Considerada**: Criar uma função utilitária de compatibilidade para verificar o atributo dinamicamente.
  - **Razão da Escolha**: O ambiente Aresta e suas dependências rodam em Python 3.13 e versões recentes do Protobuf que já suportam nativamente e de forma estável a propriedade `is_repeated`. A substituição direta mantém o código conciso, legível e em conformidade com o princípio de simplicidade do projeto.

## Risks / Trade-offs

- **Risco**: Incompatibilidade com versões muito legadas da biblioteca `protobuf` (menores que 4.x).
  - **Mitigação**: O projeto já requer e utiliza versões recentes do `protobuf`. Rodar `build.py test` após a alteração valida imediatamente a compatibilidade local e de integração.
