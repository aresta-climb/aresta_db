# Princípios de Engenharia Aresta

Para garantir que o nosso código, seja ele escrito por humanos ou por agentes autônomos de IA (como Google Antigravity e OPSX), se mantenha coeso, testável, sustentável e simples, adotamos cinco princípios basilares e inegociáveis. 

Estes princípios devem guiar toda e qualquer nova implementação ou alteração no repositório.

## I. Tudo em Português
Todo o repositório deve **OBRIGATORIAMENTE** ser em português brasileiro. Isso inclui, mas não se limita a: documentação, especificações, comentários de código, nomes de funções e até nomes de variáveis.

## II. Library-First (Biblioteca em Primeiro Lugar)
Toda funcionalidade DEVE começar como uma biblioteca independente. 
- As bibliotecas devem ser autossuficientes, testáveis de forma independente e documentadas. 
- Evite criar bibliotecas que sirvam apenas para fins organizacionais; cada biblioteca deve ter um propósito funcional claro.
- Não misture regras de negócios em grandes monólitos fortemente acoplados.

## III. Imperativo do Teste em Primeiro Lugar (TDD)
O Desenvolvimento Orientado a Testes (Test-Driven Development) é **obrigatório** e inegociável. 
- QUALQUER arquivo `.py` DEVE ter um `_test.py` acompanhando no mesmo diretório com os testes da biblioteca.
- Os testes DEVEM ser escritos e aprovados (ou melhor, devem inicialmente falhar) antes do início de qualquer implementação do código de produção. 
- O ciclo Red-Green-Refactor (Vermelho-Verde-Refatorar) deve ser estritamente seguido para cada nova tarefa e unidade lógica introduzida.

## IV. Testes de Integração em Primeiro Lugar
Priorize testar as fronteiras e os contratos entre os componentes do sistema. 
- Os testes de integração DEVEM ser estabelecidos antes dos testes unitários profundos.
- Isso garante a integridade do sistema como um todo e assegura que os requisitos funcionais inter-sistemas sejam atendidos logo no início do desenvolvimento.

## V. Simplicidade e Anti-Abstração
O código DEVE ser simples, declarativo e fácil de compreender. 
- Evite abstrações prematuras e códigos "espertos" (complexidade desnecessária). 
- Siga a regra de ouro: *"Melhor um pouco de duplicação do que a abstração errada."*
- Ao mesmo tempo, pratique o DRY (Don't Repeat Yourself) de forma prudente: evite código repetitivo se ele pode ser abstraído de forma óbvia e simples para fácil reutilização.

## VI. Edições de Estado via Comandos do Histórico (Undo/Redo)
Toda e qualquer modificação no estado do croqui (seja no Protobuf, dados, imagens ou mapas) a partir da interface gráfica do editor deve ser realizada **obrigatoriamente** através do empilhamento de comandos na pilha global de histórico (`QUndoCommand` na pilha `historico`), e nunca por mutações diretas nos callbacks dos componentes gráficos. Isso garante que o estado do editor seja sempre passível de reversão (desfazer/refazer) de forma consistente e sincronizada.

---
> **Nota para Agentes Autônomos**: Vocês estão estritamente obrigados a considerar este documento como diretriz de mais alta prioridade ao planejar arquitetura, sugerir refatorações, ou implementar novas rotinas (incluindo o uso do `opsx-apply`).
