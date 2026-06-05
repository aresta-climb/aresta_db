## Why

A medida que o desenvolvimento avança com o uso de agentes de implementação (Google Antigravity, OPSX), é essencial estabelecer um conjunto claro de princípios fundamentais. A ausência de princípios explícitos pode levar a uma base de código inconsistente, acoplada, difícil de testar e com abstrações prematuras ou erradas. Esta mudança formaliza as regras do jogo para todas as futuras implementações, garantindo qualidade, testabilidade e manutenibilidade.

## What Changes

- Estabelecimento de quatro princípios fundamentais de engenharia para o repositório:
  1. **Library-First**: Construção de bibliotecas autossuficientes e testáveis em vez de código monolítico.
  2. **Imperativo do Teste em Primeiro Lugar (TDD)**: Exigência de ciclos Red-Green-Refactor para toda tarefa.
  3. **Testes de Integração em Primeiro Lugar**: Validação primária de fronteiras e contratos.
  4. **Simplicidade e Anti-Abstração**: Foco em código declarativo, preferindo duplicação simples a abstrações erradas, com DRY prudente.
- Atualização da documentação ou diretrizes do projeto para incluir os princípios.

## Capabilities

### New Capabilities
- `principios-implementacao`: Define as diretrizes e regras fundamentais que os agentes (Antigravity, OPSX) e desenvolvedores devem seguir ao implementar funcionalidades no repositório.

### Modified Capabilities

## Impact

- Afeta todas as implementações futuras de código, APIs e sistemas no repositório.
- Define a forma de trabalho de agentes autônomos.
- Exige adaptação no planejamento de tarefas (Tasking) para acomodar rigor em TDD e Library-First.
