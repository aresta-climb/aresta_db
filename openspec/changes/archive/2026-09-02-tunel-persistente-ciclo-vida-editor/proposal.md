## Why

Atualmente, o túnel de retransmissão de prévia na Cloudflare (`previa.arestaclimb.com`) desconecta automaticamente e se torna permanentemente inacessível mesmo enquanto o Editor Desktop permanece aberto, caso o celular esteja desconectado ou inativo. Isso ocorre devido a uma combinação de fatores: descarregamento de memória do *Durable Object* na Cloudflare quando não há tráfego ativo, rejeição de reconexão no ponto de extremidade (*endpoint*) `/ws` com erro HTTP 404 (exigindo que a sessão já exista em memória volátil), tolerância curta de reconexão (60 segundos) e cancelamento agressivo de tarefas de leitura no batimento cardíaco (*heartbeat*) do cliente Python (`tunel_retransmissor.py`).

Esta alteração vincula estritamente o ciclo de vida da sessão e do túnel ao **Editor Desktop**, tratando o aplicativo móvel exclusivamente como um **cliente efêmero**. Enquanto o editor estiver aberto com o servidor ativo, o túnel se mantém vivo, resiliente a oscilações de rede e apto a receber conexões móveis a qualquer momento, pelo mesmo código de pareamento e QR Code, em estrita observância a `PRINCIPIOS.md`.

## What Changes

- **Ciclo de Vida Vinculado ao Editor Desktop**: A sessão e o túnel permanecem ativos e disponíveis durante toda a execução do Editor Desktop (ou até que o usuário clique explicitamente em "Encerrar Conexão" ou feche o croqui/aplicativo). Clientes móveis conectam e desconectam de forma totalmente efêmera sem impactar a longevidade da sessão.
- **Auto-Recuperação e Restauração de Sessão no Retransmissor Cloudflare**: Modificação do ponto de extremidade `/ws` do retransmissor para aceitar conexões com token JWT válido mesmo após reinicialização do Worker/*Durable Object*, recriando ou restaurando a sessão automaticamente para o código solicitado em vez de retornar erro HTTP 404.
- **Persistência de Metadados de Sessão no Armazenamento do Durable Object**: Armazenamento do estado da sessão (`codigo`, `usuarioId`, `criadoEm`) no armazenamento nativo (`state.storage`) do *Durable Object*, garantindo imunidade a inicializações a frio (*cold starts*) e rotação de instâncias na nuvem.
- **Eliminação de Exclusão Prematura por Ausência do Celular**: Remoção do descarte de sessão por ausência de clientes móveis ouvintes, mantendo a sessão viva enquanto houver conexão do editor ou enquanto o editor estiver em processo de reconexão.
- **Batimento Cardíaco Estável e Não Destrutivo no Python (`tunel_retransmissor.py`)**: Refatoração do laço assíncrono do cliente desktop para enviar pings periódicos em corrotina dedicada sem cancelar nem interromper a tarefa `ws.recv()`, aumentando a tolerância a variações de latência de rede.
- **Reconexão Resiliente com Reautenticação Automática**: Caso ocorra uma desconexão de rede no computador e o servidor responda com 404, o cliente do editor reexecuta transparentemente o registro de sessão mantendo o **mesmo código de 8 caracteres**, preservando o QR Code e o link exibidos ao usuário.
- **Conformidade Estrita com os Princípios de Engenharia (`PRINCIPIOS.md`)**:
  - *I. Tudo em Português*: Nomenclatura, documentação e testes 100% em português brasileiro.
  - *II. Biblioteca em Primeiro Lugar (Library-First)*: Módulos independentes e desacoplados de interface gráfica (`tunel_retransmissor.py`, `gerenciador_sessao.ts`).
  - *III. 100% de Cobertura de Testes Unitários*: Cobertura total em todos os módulos alterados.
  - *IV. Imperativo do TDD*: Ciclo Vermelho-Verde-Refatorar obrigatório com testes criados previamente.
  - *V. Testes de Integração em Primeiro Lugar*: Estabelecer testes de contrato e integração antes de testes unitários profundos.
  - *VI. Simplicidade e Anti-Abstração*: Código direto, declarativo e sem complexidade acidental.

## Capabilities

### Modified Capabilities
- `retransmissor-nuvem-previa`: Atualização dos requisitos do serviço Cloudflare Worker para suportar auto-recuperação/restauração de sessão autenticada via WebSocket, persistência de metadados no armazenamento do Durable Object e tolerância contínua a conexões de longo prazo.
- `cliente-sincronizacao-ao-vivo`: Atualização da biblioteca `tunel_retransmissor.py` no Editor Desktop para implementar batimento cardíaco não destrutivo, reautenticação automática com preservação do código e reconexão transparente.
- `servidor-celular`: Atualização dos requisitos do `ServidorCelular` para gerenciar a persistência do túnel durante toda a sessão ativa do editor.

## Impact

- **Serviço na Nuvem (`aresta_backend/cloudflare/previa`)**: Ajustes em `src/index.ts`, `src/gerenciador_sessao.ts` e testes em `test/worker.test.ts` para persistência em armazenamento e restauração automática via `/ws`.
- **Editor Desktop (`aresta_db`)**: Ajustes em `editor/core/tunel_retransmissor.py`, `editor/core/servidor_celular.py` e testes com 100% de cobertura em `editor/core/tunel_retransmissor_test.py` e `editor/core/servidor_celular_test.py`.
- **Aplicativo Móvel (`aresta_app`)**: Nenhum impacto negativo ou quebra de contrato no app Flutter; a experiência se torna transparente, permitindo conectar e reconectar no mesmo código sem erros de sessão expirada.
