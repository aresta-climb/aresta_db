# Princípios de Engenharia Aresta (`aresta_db`)

Para garantir que o nosso código, seja ele escrito por humanos ou por agentes autônomos de IA (como Google Antigravity e OPSX), se mantenha coeso, testável, sustentável e simples, adotamos oito princípios basilares e inegociáveis.

Estes princípios devem guiar toda e qualquer nova implementação, revisão ou refatoração no repositório.

## I. Tudo em Português
Todo o repositório deve **OBRIGATORIAMENTE** ser em português brasileiro. Isso inclui, mas não se limita a: documentação, especificações (OpenSpec), comentários de código, docstrings, mensagens de erro, nomes de módulos, classes, funções, métodos e variáveis.
*Exceções:* Nomes de bibliotecas de terceiros, APIs externas, termos técnicos consolidados do ecossistema e títulos de seção exigidos em inglês pelo schema do OpenSpec.

## II. Modularidade e Desacoplamento (Library-First)
Toda funcionalidade DEVE começar e ser estruturada como uma biblioteca ou módulo independente.
- As bibliotecas devem ser autossuficientes, testáveis de forma isolada e claramente documentadas.
- Evite criar arquivos ou pacotes que sirvam apenas para fins puramente organizacionais; cada módulo separado deve ter um propósito funcional claro e uma interface pública coesa.
- Não misture regras de negócios em grandes monólitos ou diretamente acopladas a componentes visuais e de infraestrutura.

## III. Testes Orientados a Comportamento e Espelhamento 1:1
Os testes devem validar **o que** o código faz (comportamento), e nunca **como** ele foi implementado internamente.
- **Espelhamento 1:1 Obrigatório**: QUALQUER arquivo `.py` de produção DEVE possuir um arquivo `_test.py` correspondente no mesmo diretório. Se decidimos separar código em um arquivo próprio, ele possui por definição uma interface pública que deve ser testada.
- **Um Teste por Comportamento (Behavior-Driven Testing)**: Cada função de teste deve verificar um único comportamento ou regra de negócio observável através da API pública do módulo (seguindo a estrutura *Dado/Quando/Então* ou *Preparar/Agir/Verificar*).
- **Proibição de Change-Detector Tests**: É estritamente proibido escrever testes acoplados à implementação interna (inspecionar atributos privados, verificar a sequência de chamadas de métodos auxiliares internos ou replicar a lógica de produção dentro do asserto). Uma refatoração interna que preserve o contrato público nunca deve quebrar os testes.

## IV. 100% de Cobertura Comportamental e TDD (Red-Green-Refactor)
O Desenvolvimento Orientado a Testes (Test-Driven Development) e a cobertura integral são **obrigatórios** e inegociáveis.
- **Ciclo Red-Green-Refactor**: Os testes DEVEM ser escritos e vistos falhar (*Red*) antes do início de qualquer implementação de código de produção (*Green*), seguidos de refatoração (*Refactor*).
- **100% de Unit Test Coverage via Comportamento**: Qualquer alteração submetida deve manter 100% de cobertura de testes atingida exclusivamente exercitando comportamentos reais pela interface pública.
- **Resolução de Cobertura pelo Design**: Se uma linha ou ramificação (`if/else`, `try/except`) não puder ser alcançada por um teste de comportamento público, **o defeito está no código de produção** (código morto, validação defensiva redundante ou acoplamento direto de I/O). A solução obrigatória é simplificar o código de produção ou remover a ramificação inalcançável — sendo proibido usar mocks internos ou chamar métodos privados para forçar cobertura artificial.

## V. Fidelidade de Produção, Anti-Mocking e Testes de Integração em Primeiro Lugar
A suíte de testes deve ser representativa do comportamento real do sistema em produção.
- **Testes de Integração em Primeiro Lugar**: Priorize testar as fronteiras e os contratos entre os componentes do sistema antes de descer para detalhes isolados.
- **Proibição de Mocks para Código Interno**: É proibido usar `unittest.mock`, `MagicMock`, `patch` ou `monkeypatch` para isolar classes, modelos Protobuf, estado ou bibliotecas internas do próprio projeto. Use sempre as implementações reais, sistema de arquivos temporário real (`tmp_path`) e bancos em memória/temporários.
- **Bibliotecas `test-only` de Fakes Determinísticos**: Para fronteiras externas (rede, GitHub, Supabase, Discord, servidores HTTP ou hardware), devem ser utilizadas **bibliotecas `test-only` de Fakes determinísticos** em memória (configuráveis inclusive para simular falhas determinísticas de I/O), evitando reimplementar stubs ad-hoc em cada arquivo de teste.
- **Fakes Também São Bibliotecas Testadas**: Toda biblioteca de Fake (`*_fake.py`) é uma biblioteca de primeira classe e DEVE obrigatoriamente possuir seu próprio arquivo de teste espelhado (`*_fake_test.py`) garantindo que o Fake cumpre fielmente o contrato real.

## VI. Simplicidade, Anti-Abstração e Documentação Contínua
O código DEVE ser simples, declarativo, bem documentado e fácil de compreender.
- Evite abstrações prematuras e códigos "espertos" (complexidade desnecessária). Siga a regra de ouro: *"Melhor um pouco de duplicação do que a abstração errada."*
- Pratique o DRY (Don't Repeat Yourself) de forma prudente: extraia apenas o que for óbvio e simples para reutilização clara.
- Mantenha docstrings explicando *o porquê* (intenção e invariantes) e atualize os arquivos `README.md` pertinentes sempre que introduzir ou alterar módulos e fluxos arquiteturais.

## VII. Inegociabilidade Perante Código Legado (Regra do Escoteiro)
A existência de código ou testes legados no repositório que ainda não sigam integralmente estes padrões **NÃO é desculpa nem precedente** para violá-los.
- Agentes autônomos e desenvolvedores estão proibidos de imitar antipadrões presentes em arquivos vizinhos (como uso de `MagicMock`/`patch`, *change-detector tests* ou identificadores em inglês).
- Sempre que tocar em um arquivo ou módulo existente que viole este `AGENTS.md`, você DEVE refatorar o trecho e os testes afetados para que passem a seguir integralmente estes princípios.

## VIII. Edições de Estado via Comandos do Histórico (Undo/Redo)
Toda e qualquer modificação no estado do croqui (seja no Protobuf, dados, imagens ou mapas) a partir da interface gráfica do editor deve ser realizada **obrigatoriamente** através do empilhamento de comandos na pilha global de histórico (`QUndoCommand` na pilha `historico`), e nunca por mutações diretas nos callbacks dos componentes gráficos. Isso garante que o estado do editor seja sempre passível de reversão (desfazer/refazer), auditoria e persistência no diário transacional de forma consistente e sincronizada.

---
> **Nota para Agentes Autônomos**: Vocês estão estritamente obrigados a considerar este documento como diretriz de mais alta prioridade ao planejar arquitetura, sugerir refatorações, ou implementar novas rotinas (incluindo o uso do OpenSpec).
