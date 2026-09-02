## 1. Testes de Integração de Fronteira em Primeiro Lugar (Princípio V)

- [ ] 1.1 (TDD - Vermelho) Escrever testes de integração em `editor/legacy_views/conexao_celular_integracao_test.py` e `test/worker.test.ts` cobrindo o contrato de comunicação entre o Editor Desktop e o Retransmissor na Cloudflare (sobrevivência do túnel após desconexão do celular e auto-recuperação de conexão após reinício do servidor).

## 2. Retransmissor na Nuvem Cloudflare: Auto-Restauração e Persistência (`aresta_backend/cloudflare/previa`)

- [ ] 2.1 (TDD - Vermelho) Escrever testes unitários em `test/worker.test.ts` cobrindo a auto-restauração de sessão com token JWT válido no ponto de extremidade `/ws` (mesmo quando a sessão não estiver presente em memória RAM), persistência de metadados no armazenamento nativo do *Durable Object* (`state.storage`) e tolerância estendida de desconexão para 10 minutos.
- [ ] 2.2 (TDD - Verde) Implementar em `src/index.ts` e `src/gerenciador_sessao.ts` a validação de JWT e auto-criação/restauração da sessão no ponto de extremidade `/ws` sem retornar 404 para conexões autenticadas válidas.
- [ ] 2.3 (TDD - Verde) Implementar no `SessaoDurableObject` a persistência e restauração do registro de sessão no `state.storage`.
- [ ] 2.4 (TDD - Verde) Ajustar a tolerância de desconexão do editor para 10 minutos (`toleranciaMs = 600_000`) e garantir que a desconexão ou ausência de clientes móveis ouvintes não encerre a sessão do editor.
- [ ] 2.5 (TDD - Refatorar) Executar a suíte de testes do Worker e garantir 100% de cobertura de testes unitários e tipagem estrita no TypeScript.

## 3. Biblioteca do Túnel: Batimento Cardíaco e Reconexão Resiliente (`tunel_retransmissor.py`)

- [ ] 3.1 (TDD - Vermelho) Escrever testes unitários em `editor/core/tunel_retransmissor_test.py` cobrindo o envio periódico de batimento cardíaco (*heartbeat*) em corrotina paralela dedicada (sem cancelamento da tarefa de leitura `ws.recv()`) e reconexão resiliente preservando o código de sessão de 8 caracteres.
- [ ] 3.2 (TDD - Verde) Refatorar o laço de execução assíncrona do `ClienteTunelRetransmissor` para executar a escuta contínua de mensagens e despachar pings periódicos em tarefa dedicada em segundo plano.
- [ ] 3.3 (TDD - Verde) Implementar suporte a reconexão automática com fornecimento de token JWT atualizado para auto-restauração no servidor retransmissor.
- [ ] 3.4 (TDD - Refatorar) Garantir 100% de cobertura de testes unitários em `editor/core/tunel_retransmissor_test.py`.

## 4. Servidor Celular e Integração com o Editor Desktop (`servidor_celular.py`)

- [ ] 4.1 (TDD - Vermelho) Escrever testes unitários em `editor/core/servidor_celular_test.py` e `editor/legacy_views/dialogo_conexao_celular_test.py` verificando a manutenção contínua do túnel em segundo plano mesmo sem celulares conectados.
- [ ] 4.2 (TDD - Verde) Atualizar `ServidorCelular` para gerenciar a longevidade do túnel atrelada estritamente ao ciclo de vida do Editor Desktop, mantendo a conexão aberta até a solicitação explícita de encerramento pelo usuário ou fechamento do workspace.
- [ ] 4.3 (TDD - Refatorar) Executar a suíte completa de testes do Editor Desktop e validar 100% de cobertura de código.
