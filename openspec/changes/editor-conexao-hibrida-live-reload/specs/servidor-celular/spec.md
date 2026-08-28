## ADDED Requirements

### Requirement: Integração com Túnel de Saída para o Retransmissor
O servidor local do Editor Desktop MUST estabelecer uma conexão de saída WebSocket com o Retransmissor na nuvem (`wss://previa.arestaclimb.com/ws?sessao=<codigo>`), registrando o código de sessão gerado e respondendo às requisições de arquivos repassadas pelo retransmissor em tempo real.

#### Scenario: Conexão e anúncio de metadados ao retransmissor
- **WHEN** o servidor celular for iniciado no Editor Desktop
- **THEN** ele deve gerar um código de sessão de 8 caracteres alfanuméricos (`[0-9a-z]`), conectar-se ao WebSocket do retransmissor e enviar mensagem com seu IP local e porta.

#### Scenario: Processamento de requisições vindas do retransmissor
- **WHEN** o servidor celular receber uma mensagem do retransmissor contendo uma requisição de leitura de arquivo (ex: `indice.binarypb` ou imagem)
- **THEN** ele deve ler o arquivo correspondente da pasta compilada e devolver os bytes de resposta formatados com cabeçalhos apropriados pelo WebSocket.

### Requirement: Emissão de eventos de recarregamento em tempo real
O servidor celular do Editor Desktop MUST expor capacidade de emitir eventos push de recarregamento para todos os clientes conectados (seja via WebSocket local ou através do túnel de retransmissão).

#### Scenario: Notificação após compilação bem-sucedida
- **WHEN** uma compilação de setor ou croqui for finalizada pelo editor
- **THEN** o servidor celular deve disparar imediatamente um evento `{"tipo": "recarregar", "setor": "<id_do_setor>"}` para os canais WebSocket ativos.
