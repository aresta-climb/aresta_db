## Context

O projeto conta cada vez mais com o apoio de agentes de implementação autônomos (Google Antigravity, agentes OPSX). Sem regras claras que definam como as implementações devem ser feitas, o código pode perder a coesão, acumular complexidade e tornar-se menos testável e confiável.

## Goals / Non-Goals

**Goals:**
- Institucionalizar as regras de "Library-First", "Test-Driven Development (TDD)", "Integration Tests First", e "Simplicity and Anti-Abstraction" no processo de desenvolvimento do repositório para orientar agentes e humanos.

**Non-Goals:**
- Criar infraestrutura técnica de testes ou frameworks novos nesta mudança. A mudança visa apenas a adoção da filosofia e documentação orientativa.

## Decisions

1. **Princípios Fixos para Agentes**: Os princípios passam a ser dogmas para o modelo mental dos agentes trabalhando no repositório. O processo OPSX e as regras de workflow devem reforçar estas heurísticas.
2. **Library-First**: Cada funcionalidade será, por padrão, extraída ou projetada como uma biblioteca separada, e não misturada em implementações acopladas.
3. **TDD Estrito**: O fluxo Red-Green-Refactor será o padrão exigido na execução das tarefas (`tasks.md`).

## Risks / Trade-offs

- **Risk**: Agentes de IA podem falhar em seguir os princípios rigorosamente, "alucinando" código de produção antes do teste.
  - **Mitigation**: Auditoria de processo, explicitando as etapas nos workflows (`/opsx-apply`), além de verificação de cobertura (CI) que impede PRs sem testes.
- **Risk**: Agentes não conseguirem configurar testes de integração de forma correta sem intervenção humana.
  - **Mitigation**: Iniciar por testes de unidade se os testes de integração forem inviáveis sem mocks pesados, mas a preferência formal é que a fronteira seja o ponto inicial do teste.
