# principios-implementacao Specification

## Purpose
Define os princípios inegociáveis de engenharia de software, arquitetura modular e testes orientados a comportamento para desenvolvedores e agentes autônomos no ecossistema Aresta.

## Requirements

### Requirement: Tudo em Português
Todo o repositório deve OBRIGATORIAMENTE ser em português, incluindo documentação, especificações, comentários de código, nomes de funções e variáveis.

#### Scenario: Escrita de código ou documentação
- **WHEN** um agente ou desenvolvedor escreve qualquer código ou documento
- **THEN** o idioma utilizado é sempre o português do Brasil.

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

### Requirement: Padronização Canônica de AGENTS.md nos Repositórios do Ecossistema
Todos os repositórios do ecossistema (`aresta_db`, `aresta_api`, `aresta_app`, `aresta_backend`, `arestaclimb.com` e `fixalog`) SHALL adotar o arquivo `AGENTS.md` na raiz como única fonte da verdade para os princípios de engenharia, eliminando arquivos legados (`PRINCIPIOS.md`, `AGENT.md`, `.agents/agents.md`) e skills duplicadas (`.agents/skills/principios_desenvolvimento/`). Os princípios I a VII MUST ser universais e consistentes entre todos os repositórios, e o princípio VIII MUST ser reservado no final do documento para as diretrizes arquiteturais específicas de cada repositório.

#### Scenario: Consulta às diretrizes de engenharia em qualquer repositório
- **WHEN** um agente autônomo ou desenvolvedor acessa a raiz de qualquer um dos 6 repositórios ou consulta `openspec/config.yaml` e documentações (`README.md`, `CONTRIBUTING.md`, `GUIA_DO_DESENVOLVEDOR.md`)
- **THEN** encontra o arquivo `AGENTS.md` estruturado com os 7 princípios universais seguidos do princípio VIII específico do repositório, sem referências residuais a `PRINCIPIOS.md` ou `AGENT.md`.

### Requirement: Testes Orientados a Comportamento e Espelhamento 1:1
Todo arquivo de código de produção separado SHALL possuir um arquivo de teste espelhado (`_test.py`, `_test.dart`, `_test.ts`, `.test.js`), pois a separação em arquivo próprio implica a existência de uma interface pública que deve ser testada. Os testes unitários MUST ser orientados a comportamento (Behavior-Driven Testing), com **um teste por comportamento** exercitando exclusivamente a API pública e efeitos observáveis, sendo estritamente proibidos *change-detector tests* (testes que inspecionam estado privado, chamadas internas ou que quebram em refatorações que preservem o comportamento).

#### Scenario: Escrita de teste unitário para um módulo
- **WHEN** um agente ou desenvolvedor escreve testes para um arquivo de produção
- **THEN** cria um teste dedicado para cada comportamento observável da interface pública daquele arquivo, sem acoplar em atributos privados ou detalhes de implementação interna.

### Requirement: 100% de Cobertura Comportamental e Resolução pelo Design
O repositório SHALL exigir 100% de cobertura de testes atingida exclusivamente através de comportamentos reais exercitados pela interface pública no ciclo TDD (Red-Green-Refactor). Caso uma linha ou ramificação não possa ser alcançada por um teste de comportamento público, o código de produção MUST ser refatorado ou ter o código morto/defensivo redundante removido, sendo proibido usar mocks internos ou chamadas a métodos privados para forçar cobertura artificial.

#### Scenario: Ramificação não coberta por testes de comportamento
- **WHEN** uma linha ou branch do código de produção não é atingida pelos testes de comportamento da API pública
- **THEN** o desenvolvedor ou agente refatora o design do código de produção (injetando a fronteira via Fake ou removendo a ramificação inalcançável) em vez de criar um teste acoplado à implementação.

### Requirement: Fidelidade de Produção, Anti-Mocking e Bibliotecas Test-Only de Fakes
O uso de mocks (`MagicMock`, `patch`, `mocktail`, `mockito`, spies internos) SHALL ser proibido para classes e módulos internos do sistema. Para fronteiras externas (rede, bancos remotos, sistema de arquivos, APIs de terceiros), os testes MUST utilizar implementações reais (como diretórios temporários, bancos em memória e servidores locais em loopback) ou **bibliotecas `test-only` de Fakes determinísticos** reutilizáveis. Toda biblioteca de Fake (`*_fake`) SHALL ser tratada como biblioteca de primeira classe e possuir seu próprio arquivo de teste espelhado (`*_fake_test`) validando a fidelidade do seu comportamento.

#### Scenario: Teste de módulo que depende de fronteira externa
- **WHEN** um módulo precisa ser testado em cenários de sucesso e de falha de uma fronteira externa
- **THEN** o teste utiliza uma biblioteca `test-only` de Fake determinístico compartilhada (que por sua vez possui testes em `*_fake_test`), sem instanciar mocks ad-hoc no arquivo de teste.

### Requirement: Inegociabilidade Perante Código Legado (Regra do Escoteiro)
A existência de código ou testes legados que não sigam os padrões definidos no `AGENTS.md` SHALL NOT servir de justificativa ou precedente para novas violações. Sempre que um arquivo existente com antipadrões (como uso de mocks, *change-detector tests* ou nomenclatura em inglês) for modificado, o trecho e seus testes correspondentes MUST ser refatorados para cumprir integralmente o `AGENTS.md`.

#### Scenario: Modificação em módulo legado com mocks
- **WHEN** um agente ou desenvolvedor precisa alterar ou adicionar um comportamento em um módulo existente que utiliza mocks ou viola o `AGENTS.md`
- **THEN** o agente não replica o antipadrão e refatora o trecho/teste tocado para seguir os princípios de testes orientados a comportamento e Fakes determinísticos.
