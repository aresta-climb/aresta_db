## Context

O Aresta Editor permite que autores compilem e visualizem croquis em tempo real em smartphones através de uma conexão híbrida (rede local e retransmissor na nuvem em `previa.arestaclimb.com`). O túnel é estabelecido pelo Editor Desktop com o Cloudflare Worker (`aresta_backend/cloudflare/previa`), gerando um código de pareamento de 8 caracteres alfanuméricos em Base36 (`k9x2-p83a`) e um QR Code correspondente.

Contudo, na arquitetura anterior, o estado da sessão no retransmissor residia puramente em memória volátil (`Map` JavaScript). Quando nenhum celular estava ativamente conectado e o WebSocket do computador sofria qualquer oscilação ou o container do *Durable Object* na Cloudflare era reciclado por inatividade (*cold start* / descarregamento de memória), a sessão era apagada. Em seguida, ao tentar reconectar, o ponto de extremidade `/ws` retornava HTTP 404, e o cliente Python entrava em ciclo de falha permanente, inutilizando o QR Code e o código já gerados. Adicionalmente, a rotina de batimento cardíaco (*heartbeat*) em Python cancelava forçadamente a corrotina `ws.recv()` a cada 15 segundos, gerando instabilidade desnecessária na leitura de mensagens.

Esta mudança refatora o ciclo de vida do túnel para vinculá-lo estritamente ao **Editor Desktop** em conformidade com `PRINCIPIOS.md`: o celular é formalmente tratado como um **cliente efêmero** (que pode conectar, desconectar, ser colocado em segundo plano ou reabrir horas depois sem quebrar a sessão), enquanto o túnel e o código permanecem vivos e auto-recuperáveis durante todo o tempo em que o Editor estiver aberto.

## Goals / Non-Goals

**Goals:**
- **Princípios de Engenharia Aresta (`PRINCIPIOS.md`)**:
  - *I. Tudo em Português*: Nomenclatura, documentação, testes e mensagens rigorosamente em português brasileiro.
  - *II. Biblioteca em Primeiro Lugar (Library-First)*: Manter toda a lógica de comunicação isolada em bibliotecas puras e desacopladas da interface gráfica (`tunel_retransmissor.py`, `gerenciador_sessao.ts`).
  - *III. 100% de Cobertura de Testes*: Cobertura integral e obrigatória de testes unitários e de integração em todos os arquivos modificados.
  - *IV. Imperativo do TDD*: Ciclo Vermelho-Verde-Refatorar estrito para cada módulo.
  - *V. Testes de Integração em Primeiro Lugar*: Estabelecer testes de contrato entre Editor e Retransmissor antes de testes unitários aprofundados.
  - *VI. Simplicidade e Anti-Abstração*: Implementações diretas, sem complexidade acidental ou abstrações prematuras.
- **Ciclo de Vida Vinculado ao Editor**: O túnel e o código de pareamento duram enquanto o Editor Desktop mantiver a conexão de prévia ativa, sobrevivendo à ausência ou desconexão de clientes móveis.
- **Cliente Celular Efêmero**: O aplicativo móvel pode conectar, desconectar e reconectar a qualquer momento sem afetar o estado do túnel no computador.
- **Auto-Recuperação no Cloudflare Worker (`/ws`)**: Se o Worker for reciclado ou reiniciar, conexões WebSocket com token JWT válido recriam/restauram a sessão imediatamente para aquele mesmo código, eliminando erros 404 indevidos na reconexão.
- **Persistência de Sessão no Armazenamento do Durable Object**: Persistir os metadados fundamentais da sessão (`codigo`, `usuarioId`, `metadados`, `criadoEm`) no armazenamento nativo (`state.storage`) do *Durable Object*, garantindo tolerância a inicializações a frio (*cold starts*).
- **Batimento Cardíaco Assíncrono Não Destrutivo no Python**: Refatorar `ClienteTunelRetransmissor` para emitir pings periódicos via tarefa em segundo plano (*background task*) sem cancelar a tarefa `ws.recv()`, aumentando a estabilidade do fluxo de dados.
- **Reautenticação e Re-registro Automático com Mesmo Código**: Se a conexão cair e o Worker exigir re-registro, o Editor Desktop reautentica no Cloudflare reutilizando o mesmo código de 8 caracteres, sem alterar o QR Code na tela.

**Non-Goals:**
- Persistir arquivos compilados ou binários de croquis em banco de dados ou armazenamento em nuvem (o tráfego permanece 100% streaming efêmero em memória RAM entre Editor e Celular).
- Modificar o aplicativo Flutter (`aresta_app`) além do necessário (o aplicativo móvel já consome a URL canônica e se beneficiará diretamente da estabilidade do túnel).

## Decisions

### 1. Auto-Restauração de Sessão no Ponto de Extremidade `/ws` com JWT Válido
- **Decisão**: Quando o Editor Desktop conecta a `wss://previa.arestaclimb.com/ws?sessao=<codigo>&token=<jwt>`, caso o código não esteja presente na memória RAM do Worker (por exemplo, após reinício de container), o Worker valida o JWT do Supabase. Se o token for válido e corresponder ao usuário autorizado, o Worker recria a sessão para aquele mesmo código em vez de retornar HTTP 404.
- **Racional**: Elimina a fragilidade onde uma inicialização a frio (*cold start*) na Cloudflare invalidava irremediavelmente a sessão do usuário no computador.
- **Alternativa Considerada**: Exigir sempre um novo `POST /sessoes` gerando um novo código aleatório a cada queda. *Rejeitada*: isso invalidaria o QR Code e o código já escaneado ou digitado no celular do usuário.

### 2. Persistência de Metadados no Armazenamento do Durable Object
- **Decisão**: Ao criar ou restaurar uma sessão, salvar `{ codigo, usuarioId, usuarioEmail, metadados, criadoEm }` no `this.state.storage` do *Durable Object*.
- **Racional**: Garante que o estado da sessão sobreviva ao descarregamento da memória do DO quando nenhum WebSocket estiver trafegando dados por alguns minutos.

### 3. Batimento Cardíaco Assíncrono Dedicado no Python sem Cancelamento de `ws.recv()`
- **Decisão**: No `ClienteTunelRetransmissor`, separar a escuta de mensagens (`ws.recv()`) do envio de pings. O laço principal executa a recepção contínua enquanto uma corrotina paralela (`_loop_heartbeat`) envia pings a cada 30 segundos (`ping_interval=30.0, ping_timeout=30.0`).
- **Racional**: Evita cancelar repetidamente a corrotina de leitura do `websockets`, prevenindo erros de concorrência e fechamentos espúrios de conexão.

### 4. Tolerância Estendida de Desconexão (10 minutos) e Encerramento Gracioso
- **Decisão**: Aumentar a tolerância de reconexão do editor no Worker de 60 segundos para 10 minutos (`toleranciaMs = 600_000`). O encerramento definitivo e descarte ocorrem se o editor não reconectar após 10 minutos, ou se o usuário explicitamente solicitar o encerramento da prévia.
- **Racional**: Dá tempo suficiente para o computador do usuário trocar de rede Wi-Fi, retornar de suspensão rápida ou superar oscilações temporárias de provedor de internet.

## Risks / Trade-offs

- **[Risco] Expiração do Token JWT durante longas sessões de edição** → *Mitigação*: O Editor Desktop utiliza `GerenciadorSessao.recuperar_token(auto_renovar=True)` para obter tokens atualizados do Supabase antes de qualquer operação de reautenticação ou reconexão no túnel.
- **[Risco] Sessões zumbis acumuladas no Durable Object se o Editor fechar abruptamente (encerramento forçado / falta de energia)** → *Mitigação*: O temporizador de tolerância (10 minutos) e uma varredura periódica de inatividade máxima (24 horas) removem automaticamente sessões abandonadas do armazenamento.
