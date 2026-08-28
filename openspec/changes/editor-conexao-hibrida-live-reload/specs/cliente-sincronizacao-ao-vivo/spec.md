## ADDED Requirements

### Requirement: Pareamento simplificado por código curto e links diretos
O sistema cliente (aplicativo móvel) MUST permitir conexão tanto por escaneamento de QR Code contendo o link `https://previa.arestaclimb.com/<codigo>` quanto pela digitação manual de código de 8 caracteres alfanuméricos (`k9x2-p83a`), normalizando automaticamente a entrada (removendo hifens e convertendo para minúsculas).

#### Scenario: Digitação manual com formatação flexível
- **WHEN** o usuário digitar `K9X2-P83A` ou `k9x2p83a` no campo de conexão manual do aplicativo móvel
- **THEN** o aplicativo deve normalizar a string para `k9x2p83a` e iniciar o processo de conexão para a URL canônica correspondente.

#### Scenario: Abertura via link direto
- **WHEN** o usuário abrir um link do tipo `https://previa.arestaclimb.com/<codigo>` no dispositivo móvel
- **THEN** o aplicativo Aresta deve abrir diretamente na tela de conexão e iniciar o pareamento experimental com a sessão especificada.

### Requirement: Resolução híbrida inteligente de conexão (Rede Local em Primeiro Lugar)
O sistema cliente (aplicativo móvel) MUST consultar as informações da sessão no Retransmissor da Cloudflare, obter a URL local anunciada pelo editor e executar uma disputa em paralelo testando a rede local com tempo limite curto (800ms a 1.2s).

#### Scenario: Rede local disponível
- **WHEN** o dispositivo móvel receber a URL local do editor e a requisição de teste `GET /handshake` no IP local responder com sucesso dentro do tempo limite
- **THEN** o aplicativo deve definir a URL base ativa como o endereço local para máxima velocidade de carregamento.

#### Scenario: Falha ou tempo limite na rede local
- **WHEN** a requisição de teste para o endereço local falhar por tempo limite, rota inacessível ou recusa de conexão
- **THEN** o aplicativo deve selecionar automaticamente a URL do Retransmissor na Cloudflare (`https://previa.arestaclimb.com/<codigo>`) como canal ativo de comunicação.

### Requirement: Sincronização e recarregamento em tempo real no aplicativo móvel
O aplicativo móvel MUST conectar-se ao canal de eventos WebSocket da sessão ativa e escutar mensagens de notificação push de recarregamento.

#### Scenario: Recebimento de evento de recarregamento
- **WHEN** o aplicativo móvel receber uma mensagem WebSocket do tipo `{"tipo": "recarregar", "setor": "<id>"}`
- **THEN** o aplicativo deve invalidar o cache de memória do setor especificado, realizar o download dos arquivos modificados através da URL ativa (rede local ou retransmissor) e atualizar a renderização do croqui na tela sem intervenção do usuário.
