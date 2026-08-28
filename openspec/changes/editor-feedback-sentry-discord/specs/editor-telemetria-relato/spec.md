## ADDED Requirements

### Requirement: Captura de evento de relato no Sentry
A biblioteca de telemetria DEVE fornecer função para captura explícita de relatos do usuário via Sentry SDK com escopo isolado e metadados contextuais.

#### Scenario: Envio de relato com tags de contexto
- **WHEN** a função de envio de relato no Sentry é executada com mensagem, categoria, dados de diagnóstico e identificadores do croqui
- **THEN** o Sentry SDK despacha um evento com nível `info` ou `warning`, associado às tags `categoria_relato`, `id_croqui`, `commit_base_sha` e retorna o `event_id` gerado.

### Requirement: Anexo de imagem capturada e diário anonimizado
O sistema DEVE anexar o arquivo binário da imagem anotada e os comandos recentes do diário anonimizado ao evento de relato do Sentry.

#### Scenario: Anexo da imagem anotada
- **WHEN** bytes de imagem PNG são fornecidos para o envio de relato
- **THEN** o Sentry SDK inclui o anexo `captura_anotada.png` no escopo do evento.

#### Scenario: Anexo do histórico de comandos do diário
- **WHEN** houver um `GerenciadorDiario` ou pilha de comandos em edição no momento do relato
- **THEN** os comandos recentes são exportados de forma anonimizada e gravados no contexto do evento do Sentry.

### Requirement: Retorno do identificador único do evento (event_id)
A biblioteca DEVE retornar a string com o identificador único gerado pelo Sentry para viabilizar ligações diretas em canais externos.

#### Scenario: Obtenção bem-sucedida do identificador do evento
- **WHEN** o evento é recebido e processado pelo Sentry SDK
- **THEN** a função retorna a representação em string hexadecimal do `event_id`.

#### Scenario: Falha ou ausência do SDK Sentry
- **WHEN** o SDK do Sentry não estiver inicializado ou falhar
- **THEN** a função retorna `None` sem propagar exceção não tratada.
