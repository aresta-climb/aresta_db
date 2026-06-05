---
name: principios_desenvolvimento
description: Princípios inegociáveis de engenharia de software para agentes autônomos. Leia esta skill ANTES de iniciar o planejamento ou a execução de código no repositório.
---

# Princípios Básicos e Obrigatórios de Desenvolvimento

Ao atuar neste repositório (Aresta), você **deve** operar seguindo as seguintes heurísticas em toda a extensão do seu ciclo de vida (análise, planejamento, implementação e refatoração):

1. **Tudo em Português**:
   - Todo o repositório deve OBRIGATORIAMENTE ser em português, da documentação às especificações, comentários de código, nomes de funções e variáveis.

2. **Library-First (Biblioteca em Primeiro Lugar)**:
   - Todo novo recurso ou lógica pesada de negócios DEVE ser construído como uma biblioteca independente ou pacote isolado.
   - Evite scripts monolíticos acoplados. Garanta que a biblioteca seja autossuficiente e testável de forma unitária.

3. **Imperativo do TDD (Test-Driven Development)**:
   - Os testes não são opcionais e não devem ser deixados para depois da implementação.
   - Aja no fluxo **Red-Green-Refactor**: crie os testes (ou o cenário de teste), certifique-se de que eles não passam, implemente o código mínimo necessário para passá-los e, em seguida, refatore.

4. **Testes de Integração em Primeiro Lugar**:
   - Antes de testar em profundidade a lógica interna de uma classe, priorize escrever testes que verifiquem os contratos e as fronteiras com outros sistemas/módulos.

5. **Simplicidade e Anti-Abstração**:
   - Evite criar classes genéricas, fábricas (factories) ou hierarquias complexas de herança, a menos que existam múltiplos casos de uso evidentes.
   - "Melhor um pouco de duplicação do que a abstração errada."
   - Prefira código declarativo, limpo e direto.

6. **Design e Estruturação de Protobuf (aresta_api)**:
   - **Encapsulamento de Enums**: Todo novo enum deve ser chamado `Enum` e ser encapsulado por uma mensagem com o nome do enum. Essa mensagem conterá apenas o `Enum`. Isso garante o encapsulamento adequado sem necessidade de prefixos redundantes.
   - **Valor Padrão de Enums**: Todo novo enum deve obrigatoriamente iniciar com `INDEFINIDO = 0;`.
   - **Encapsulamento de Oneofs**: Todo novo `oneof` deve ser encapsulado em uma mensagem dedicada, contendo a anotação `(aresta.mensagem_formato_na_ui) = ONEOF_CONTEUDO;` na mensagem que o envolve.

**Ação Exigida**: Ao iniciar qualquer tarefa de desenvolvimento (`opsx-apply`, `opsx-propose`, ou codificação direta), incorpore imediatamente esses 6 princípios na sua heurística de trabalho.
