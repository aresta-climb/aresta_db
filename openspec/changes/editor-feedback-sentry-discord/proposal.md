## Why

Durante o uso do Editor Aresta por colaboradores e autores de croquis, encontrar comportamentos inesperados, dúvidas de usabilidade ou sugestões de melhoria exige atualmente a abertura manual de chamados em canais externos sem o devido contexto técnico.

Implementar um mecanismo nativo de envio de relatos e opiniões no Editor Aresta — permitindo capturar a imagem da janela ativa, desenhar anotações e aplicar tarjas pretas de privacidade, acompanhado do envio de um snapshot de telemetria no Sentry (com diário recente de comandos, logs e commit base) e notificação visual instantânea no Discord com link direto para o evento — conecta os autores diretamente aos desenvolvedores com reprodutibilidade determinística de 100% dos problemas reportados.

## What Changes

- **Captura e Anotação de Tela**: Implementação de captura visual da janela ativa (`window.grab()`) com ferramentas interativas de desenho (caneta livre, retângulo de destaque, cores) e tarja preta de privacidade para ocultação irreversível de dados sensíveis antes do envio.
- **Diálogo Modal Unificado de Relato**: Interface para categorizar o relato (Erro/Falha, Sugestão/Melhoria, Dúvida/Geral), adicionar comentários e visualizar a prévia das anotações em tempo real.
- **Pontos de Acesso na Interface do Usuário**:
  - Ação dedicada na barra superior (`toolbar_superior`) e atalhos globais (`F12` e `Ctrl+Shift+F`) na Janela Principal (`area_principal.py`).
  - Botão de envio de relato na Tela de Seleção de Croquis (`tela_de_carregamento.py`).
  - Botão de reporte na Tela de Abertura e Login (`tela_de_abertura.py`).
- **Snapshot de Telemetria no Sentry**: Envio de evento enriquecido no Sentry com a imagem anotada anexada, tags de contexto (`id_croqui`, `commit_base_sha`), registros de logs recentes e o histórico anonimizado do diário de comandos (`QUndoCommand`s), retornando o identificador único `event_id`.
- **Notificação Visual no Webhook do Discord**: Envio de requisição multipart com cartão visual incorporado (embed colorido, descrição, autor, sistema operacional, croqui ativo, imagem anexada) e link direto para o evento correspondente no painel do Sentry.
- **Envio Assíncrono e Resiliente**: Execução em segundo plano (`QThread`) sem bloqueio da interface gráfica, com confirmação visual via `NotificacaoToast` e tratamento resiliente para operação sem conexão.

## Capabilities

### New Capabilities
- `editor-relato-usuario`: Interface gráfica de envio de relatos com captura de tela da janela, quadro interativo para anotações e tarjas de privacidade, categorização de relatos e acionamento nos pontos de entrada do editor.
- `editor-notificacao-discord`: Cliente HTTP para despacho multipart/form-data de mensagens e cartões visuais incorporados com anexos de imagem e links de rastreabilidade para webhooks do Discord.
- `editor-telemetria-relato`: Extensão da biblioteca de telemetria do Sentry para capturar eventos manuais de relato de usuário com anexos binários (captura de tela anotada e diário de comandos anonimizado), gerando `event_id` para correlação externa.

### Modified Capabilities

## Impact

- **Código Afetado**:
  - `editor/core/telemetria.py` (métodos de envio de relato e anexo de imagens ao Sentry).
  - `editor/core/cliente_webhook_discord.py` (nova biblioteca cliente para envio ao Discord).
  - `editor/core/coletor_relato.py` (consolidação de metadados de diagnóstico e empacotamento do relato).
  - `editor/views/widget_quadro_anotacao.py` (novo componente gráfico de desenho e tarjas).
  - `editor/views/dialogos/dialogo_relato_usuario.py` (novo diálogo modal de relato).
  - `editor/views/estilo.py` (novos ícones para relato, anotação e tarja).
  - `editor/legacy_views/area_principal.py`, `editor/legacy_views/tela_de_carregamento.py`, `editor/views/tela_de_abertura.py` (inclusão dos botões de acionamento).
- **Dependências**: Utiliza estritamente bibliotecas padrão do Python (`urllib.request` / `sentry_sdk`) e PyQt6 (`QPainter`, `QImage`, `QPixmap`, `QThread`), sem adicionar dependências pesadas externas.
