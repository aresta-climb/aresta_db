# cliente-sincronizacao-ao-vivo Specification

## Purpose

Define o protocolo de códigos de sessão, pareamento, túnel de retransmissão e sincronização em tempo real ou estática entre o Editor Desktop, instâncias de prévia de Pull Request e o aplicativo móvel Aresta Climb.

## Requirements

### Requirement: Heartbeat assíncrono não destrutivo no cliente Desktop
A biblioteca `ClienteTunelRetransmissor` MUST executar o envio de pings periódicos de *heartbeat* em uma rotina assíncrona dedicada em segundo plano, sem interromper ou cancelar tarefas ativas de leitura `ws.recv()`.

#### Scenario: Envio de keepalive com canal ocioso
- **WHEN** o túnel WebSocket estiver conectado e nenhum tráfego de requisições proxy estiver sendo trafegado pelo canal
- **THEN** o cliente desktop deve emitir pings periódicos mantendo a conexão aberta com o Cloudflare Worker sem provocar exceções de cancelamento na escuta de mensagens.

### Requirement: Reconexão e auto-recuperação transparente do código de sessão
A biblioteca `ClienteTunelRetransmissor` MUST tentar reconectar automaticamente em caso de queda de rede, renovando o token JWT quando necessário e mantendo inalterado o código de sessão de 8 caracteres (`[0-9a-z]`).

#### Scenario: Reconexão com preservação de código
- **WHEN** ocorrer uma perda temporária de conectividade com a internet no computador do usuário
- **THEN** o cliente do túnel deve tentar reconectar em intervalos exponenciais com o mesmo código de sessão até o restabelecimento da conexão ou parada explícita.

### Requirement: Esquema de códigos de sessão ilimitados e reserva do prefixo de Pull Request
As bibliotecas de validação e formatação de códigos de sessão no Editor Desktop e no aplicativo móvel MUST suportar códigos alfanuméricos em Base36 com tamanho mínimo de 8 caracteres (`>= 8`, *unbounded*), mantendo 8 caracteres como padrão e reservando o prefixo `pr` exclusivamente para instâncias de Pull Request.

#### Scenario: Formatação e extração de código de Pull Request com até 6 dígitos
- **WHEN** o número da Pull Request possuir até 6 dígitos (ex: PR `#42`)
- **THEN** o código gerado deve ser preenchido com zeros à esquerda para totalizar 8 caracteres Base36 (`pr000042`) e formatado com hífen após o quarto caractere (`pr00-0042`), mantendo compatibilidade com validadores de 8 caracteres

#### Scenario: Formatação e extração de código de Pull Request com mais de 6 dígitos
- **WHEN** o número da Pull Request possuir mais de 6 dígitos (ex: PR `#1234567`)
- **THEN** o código normalizado deve conter o prefixo `pr` seguido de todos os dígitos (`pr1234567`, 9 caracteres) e ser aceito normalmente pelos validadores do Editor e do aplicativo móvel

#### Scenario: Identificação de código pertencente a Pull Request
- **WHEN** um código normalizado iniciar com `pr` seguido exclusivamente por dígitos com valor inteiro positivo
- **THEN** a biblioteca identifica o código como uma sessão estática de Pull Request e extrai o número inteiro correspondente da PR

### Requirement: Conexão via Deep Link de prévia e supressão de Live Reload para Pull Requests
O aplicativo móvel MUST interceptar Deep Links de `previa.arestaclimb.com` e `aresta://previa/*` para conectar automaticamente à sessão experimental e MUST suprimir a conexão WebSocket de Live Reload (`/events`) quando o código pertencer a uma Pull Request (`pr*`).

#### Scenario: Clique em link de prévia da Pull Request no celular
- **WHEN** o usuário clicar em `https://previa.arestaclimb.com/pr00-0042` ou `aresta://previa/pr00-0042` em um dispositivo Android ou iOS com o aplicativo instalado
- **THEN** o aplicativo intercepta o link, conecta à instância experimental `pr00-0042`, sincroniza o índice e navega automaticamente para o croqui sem iniciar o loop de reconexão WebSocket em `/pr000042/events`

#### Scenario: Abertura de link de resumo visual no Android
- **WHEN** um link `https://previa.arestaclimb.com/resumo/<codigo_pr>` for aberto em um dispositivo Android
- **THEN** o sistema não deve tratá-lo como código de sessão interna do app, garantindo sua abertura no navegador web para visualização do relatório `resumo.html`
