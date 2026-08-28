## ADDED Requirements

### Requirement: Formatação de cartão do Discord com anexo de imagem
O sistema DEVE formatar dados no padrão de Webhooks do Discord contendo cartões visuais (embeds) ricos categorizados por cor e a imagem anotada anexada via `multipart/form-data`.

#### Scenario: Geração de requisição com anexo de imagem
- **WHEN** o cliente do Discord é invocado com título, descrição, categoria, metadados e bytes da imagem PNG
- **THEN** o sistema monta uma requisição HTTP POST `multipart/form-data` com a parte JSON contendo o cartão incorporado e a parte binária contendo o arquivo `captura_anotada.png`, referenciado no cartão visual como `attachment://captura_anotada.png`.

#### Scenario: Diferenciação visual por categoria de relato
- **WHEN** a categoria do relato for "Erro / Falha"
- **THEN** a cor lateral do cartão incorporado DEVE ser vermelha (`0xDC3545`).
- **WHEN** a categoria do relato for "Sugestão / Melhoria"
- **THEN** a cor lateral do cartão incorporado DEVE ser azul (`0x2B579A`).
- **WHEN** a categoria do relato for "Dúvida / Geral"
- **THEN** a cor lateral do cartão incorporado DEVE ser verde (`0x28A745`).

### Requirement: Inclusão de link de rastreabilidade para o Sentry
O sistema DEVE incluir no cartão visual do Discord o link direto de busca ou visualização do evento no Sentry quando um identificador de evento (`event_id`) estiver disponível.

#### Scenario: Inclusão de URL do Sentry no cartão do Discord
- **WHEN** o snapshot de telemetria no Sentry retorna um identificador de evento válido
- **THEN** o cartão do Discord inclui um campo com link formatado em Markdown para o painel do Sentry (`https://o4511980548849664.sentry.io/issues/?query=event.id%3A{event_id}`).

#### Scenario: Envio sem telemetria do Sentry
- **WHEN** o envio ao Sentry não estiver disponível ou falhar
- **THEN** o cartão do Discord é despachado normalmente indicando "Telemetria Sentry: Não disponível".

### Requirement: Resiliência e tratamento de erros do Webhook
O sistema DEVE validar o status da resposta HTTP do webhook do Discord e registrar falhas detalhadas em logs sem interromper a execução do aplicativo.

#### Scenario: Resposta de sucesso do Discord
- **WHEN** o webhook do Discord responde com status HTTP 200 ou 204
- **THEN** a biblioteca retorna confirmação de sucesso.

#### Scenario: Resposta de erro do Discord
- **WHEN** o webhook do Discord responde com status 4xx ou 5xx
- **THEN** a biblioteca registra o erro nos logs estruturados e propaga exceção tipada em português para tratamento pela interface gráfica.
