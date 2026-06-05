## ADDED Requirements

### Requirement: Agentes e Desenvolvedores Seguem Library-First
Todas as implementações DEVEM ser estruturadas com a abordagem "Library-First", favorecendo a criação de pacotes/bibliotecas isolados e testáveis, em vez de implementações monolíticas acopladas.

#### Scenario: Criação de nova funcionalidade
- **WHEN** um agente ou desenvolvedor inicia uma nova implementação
- **THEN** o código é desenvolvido como um pacote ou biblioteca autossuficiente e independente desde o princípio.

### Requirement: Prática Mandatória de TDD
O desenvolvimento orientado a testes (Test-Driven Development) DEVE ser estritamente seguido, aplicando o ciclo Red-Green-Refactor em todas as novas tarefas.

#### Scenario: Implementação de código
- **WHEN** uma nova lógica de negócios ou componente precisa ser criado ou alterado
- **THEN** os testes DEVEM ser escritos e vistos falhar (Red) antes que a implementação seja desenvolvida (Green).

### Requirement: Priorização de Testes de Integração
Os testes de integração DEVEM ser escritos antes de testes unitários profundos quando a funcionalidade envolve contratos ou fronteiras entre componentes.

#### Scenario: Testando fronteiras
- **WHEN** uma nova funcionalidade exige comunicação entre módulos diferentes
- **THEN** os testes de integração que validam esse contrato devem ser criados e priorizados no início do ciclo de testes.

### Requirement: Simplicidade e Anti-Abstração
O código desenvolvido DEVE ser simples e declarativo. Abstrações prematuras DEVEM ser evitadas sob o princípio de que "é melhor uma leve duplicação do que a abstração errada", mantendo as vantagens do DRY sem engenharia excessiva.

#### Scenario: Decisão de arquitetura local
- **WHEN** um agente precisa decidir entre generalizar uma função ou manter sua simplicidade
- **THEN** a solução deve preferir a clareza e simplicidade, evitando padrões de design e abstrações genéricas até que exista uma necessidade comprovada por múltiplos casos de uso.
