## Context

Atualmente, o Aresta Editor permite que autores compilem e visualizem croquis em tempo real em seus smartphones através de um servidor HTTP local (`servidor_celular.py`). No entanto, esse método falha com frequência devido a isolamento de clientes (AP isolation) em redes Wi-Fi públicas/visitantes, roteadores que não roteiam tráfego entre sub-redes distintas (ex: PC em Ethernet e celular no Wi-Fi), firewalls locais do sistema operacional (Windows Defender) e celulares conectados à rede celular (4G/5G).

Além disso, não existe um mecanismo de notificação push em tempo real que faça o aplicativo móvel recarregar automaticamente a tela quando um croqui for editado ou salvo no computador, nem forma de compartilhar a prévia instantaneamente com parceiros de escalada remotos.

Para resolver esse problema de forma sustentável, simples e modular (em estrita observância a `PRINCIPIOS.md`), adotamos uma arquitetura orientada a bibliotecas independentes (Library-First) e testes rigorosos (TDD com 100% de cobertura): o editor tenta a conexão direta via rede local e, concorrentemente, mantém um túnel de saída WebSocket para um Cloudflare Worker leve em `previa.arestaclimb.com`, que atua como intermediário de descoberta e streaming reverso em memória RAM.

## Goals / Non-Goals

**Goals:**
- **Biblioteca em Primeiro Lugar (Library-First)**: Estruturar toda a lógica em bibliotecas independentes, testáveis e desacopladas de componentes de interface (`codigo_sessao.py`, `tunel_retransmissor.py`).
- **100% de Cobertura e TDD**: Escrever testes de integração e unitários prévios no ciclo Vermelho-Verde-Refatorar para 100% dos novos arquivos e alterações.
- **Tudo em Português**: Toda a nomenclatura de classes, funções, variáveis, comentários e testes em português brasileiro estrito.
- **Pareamento Humano**: Prover pareamento universal via código curto de 8 caracteres alfanuméricos em Base36 (`[0-9a-z]`, ex: `k9x2-p83a`) e URL correspondente (`https://previa.arestaclimb.com/<codigo>`).
- **Retransmissão em Memória**: Implementar um Cloudflare Worker como retransmissor efêmero que faz o proxy de requisições HTTP do celular para o WebSocket do computador 100% em memória RAM, sem qualquer persistência no Supabase.
- **Conexão Híbrida Inteligente**: Disputa paralela de conexão: tenta a rede local primeiro (máxima velocidade e economia de dados) e faz fallback transparente para a nuvem caso a rede local falhe.
- **Sincronização em Tempo Real**: Canal de eventos WebSocket para notificar o aplicativo móvel sobre alterações em croquis compilados, disparando a atualização automática de tela.
- **Compartilhamento Remoto**: Permitir o envio de links de prévia ao vivo para colaboradores remotos via links diretos (`https://previa.arestaclimb.com/<codigo>`).
- **Ciclo de Vida Limpo**: Encerramento imediato de sessões no fechamento do editor, batimento cardíaco de 30 segundos para detectar quedas e expiração de sessões inativas em 20-30 minutos.

**Non-Goals:**
- Persistir arquivos compilados ou imagens em tabelas de banco de dados ou buckets de armazenamento em nuvem (o tráfego é puramente streaming em memória).
- Implementar edição concorrente ou mutação remota de banco de dados pelo celular (o aplicativo atua exclusivamente como visualizador/revisor do estado do editor).
- Depender de binários externos de terceiros (como executáveis compilados do ngrok ou cloudflared) no computador do usuário.

## Decisions

### 1. Separação em Bibliotecas Modulares (Library-First)
- **Decisão**: Dividir as responsabilidades do lado do Editor em duas bibliotecas puras e autossuficientes:
  1. `editor/core/codigo_sessao.py`: Responsável exclusivamente por gerar códigos aleatórios criptograficamente seguros em Base36, formatar com hifens, validar formato e normalizar entradas vindas do usuário.
  2. `editor/core/tunel_retransmissor.py`: Responsável exclusivamente pela gestão do socket cliente com o retransmissor na nuvem, anúncio de metadados, processamento de requisições de arquivos repassadas e emissão de eventos push.
- **Racional**: Garante testabilidade unitária isolada de 100%, sem dependência de widgets do PyQt6 ou do loop gráfico principal da interface.
- **Alternativas descartadas**: Implementar toda a lógica de túnel e código diretamente dentro da classe `ServidorCelular` ou em callbacks da janela gráfica (descartado por violar o princípio de modularidade e desacoplamento).

### 2. Cloudflare Worker com Retransmissão WebSocket em Memória
- **Decisão**: Utilizar um Cloudflare Worker hospedado em `previa.arestaclimb.com` para gerenciar sessões temporárias identificadas por códigos de 8 caracteres e atuar como proxy reverso de streaming via WebSocket.
- **Racional**: Os Workers da Cloudflare oferecem suporte nativo a WebSockets de longa duração, consumo nulo de CPU durante espera de I/O de rede (WebSocket Hibernation API), 100.000 requisições diárias gratuitas e latência global ultrabaixa. Além disso, elimina completamente a necessidade de instalar binários externos no PC do usuário.
- **Alternativas descartadas**:
  - *Supabase Edge Functions / Storage*: Descartado por ser stateless por requisição (dificultando o roteamento direto em memória sem salvar em disco/storage) e por introduzir custos desnecessários de persistência e limpeza periódica.
  - *Binário do cloudflared embarcado*: Descartado pela complexidade de empacotamento multi-plataforma e riscos de falso positivo em antivírus no Windows.

### 3. Formato de Código Alfanumérico de 8 Caracteres (Base36)
- **Decisão**: Gerar códigos de sessão com 8 caracteres em Base36 (`[0-9a-z]`, ex: `k9x2-p83a`).
- **Racional**: Oferece $36^8 \approx 2,82 \text{ trilhões}$ de combinações possíveis, garantindo imunidade a ataques de força bruta com limitação de taxa (rate limiting) na Cloudflare. Permite formatação amigável com hífen e normalização automática no app (aceitando maiúsculas/minúsculas e com/sem hífen).
- **Alternativas descartadas**:
  - *UUID v4 completo com token secreto separado*: Mais longo e inviabilizaria a digitação manual de fallback no celular.
  - *Código puramente numérico de 4 ou 6 dígitos*: Espaço amostral reduzido frente ao Base36.

### 4. Conexão Híbrida Inteligente com Resolução de Descoberta
- **Decisão**: Quando o editor conecta ao retransmissor, ele informa seu IP e porta locais no payload inicial. Ao conectar pelo código no celular, o app recebe o endereço local e dispara um teste em paralelo com tempo limite curto (~800ms). Se a rede local responder, o app consome diretamente do IP local; se falhar, utiliza o túnel da Cloudflare.
- **Racional**: Garante a melhor experiência possível: velocidade de transferência nativa de gigabit quando na mesma rede e 100% de disponibilidade mesmo em 4G ou redes restritivas, sem que o usuário precise configurar IPs ou portas manualmente.

### 5. Sincronização em Tempo Real via Notificações Push WebSocket
- **Decisão**: Manter um canal de eventos WebSocket ativo entre Editor e App (seja direto na rede local ou através do retransmissor). Quando o editor compila uma alteração, emite `{"tipo": "recarregar", "setor": "<id>"}`. O app recebe o sinal, invalida os caches de memória e solicita os arquivos atualizados via HTTP GET.
- **Racional**: Elimina consultas periódicas (polling agressivo que drena bateria e CPU do celular) e provê feedback visual quase instantâneo (< 50ms).

## Risks / Trade-offs

- **[Risco] Tamanho de fotos grandes no Retransmissor** → *Mitigação*: O editor de croquis do Aresta já executa otimização e compressão prévia de imagens (`.webp` dimensionadas para tela mobile), mantendo o tráfego em poucos kilobytes/megabytes por requisição.
- **[Risco] Queda abrupta de conexão do Editor (crash ou suspensão)** → *Mitigação*: Implementação de batimento cardíaco periódico (ping/pong a cada 30 segundos) no WebSocket. Se o editor parar de responder, o Worker descarta a sessão imediatamente.
- **[Risco] Tentativas de força bruta em códigos de sessão** → *Mitigação*: Limitação de taxa na borda da Cloudflare (máximo de 5 a 10 erros consecutivos por IP a cada 15 minutos resultando em bloqueio HTTP 429).
