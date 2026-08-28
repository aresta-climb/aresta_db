## Context

O Editor Aresta é uma aplicação desktop desenvolvida em Python e PyQt6 com arquitetura MVC e empacotamento Windows. Recentemente, foi implementado o sistema de telemetria silenciosa e diário de comandos transacional via Sentry SDK (`editor/core/telemetria.py` e `editor/core/diario.py`).

No entanto, quando os usuários encontram comportamentos visuais inesperados, dúvidas sobre croquis ou desejam sugerir melhorias de fluxo, não existe um canal direto no aplicativo para relatar o problema com evidência visual.

Esta mudança introduz um fluxo completo de envio de relatos visuais e diagnóstico técnico, respeitando integralmente os [PRINCIPIOS.md](file:///c:/Renato/Devel/aresta-climb/aresta_db/PRINCIPIOS.md) do projeto: captura a janela ativa, fornece um quadro de anotação com tarja preta de privacidade, envia o snapshot técnico para o Sentry (com logs, replay de comandos e commit base) e publica um cartão visual formatado no Webhook do Discord com a imagem anotada e o link direto para a sessão no Sentry.

## Goals / Non-Goals

**Goals:**
- Implementar biblioteca `editor/core/coletor_relato.py` para consolidação dos metadados de diagnóstico (versão do aplicativo, sistema operacional, resolução de tela, autor ativo, identificador do croqui e commit SHA base).
- Implementar biblioteca `editor/core/cliente_webhook_discord.py` para despacho HTTP `multipart/form-data` de mensagens formatadas e anexos binários de imagem para webhooks do Discord usando a biblioteca padrão do Python (`urllib.request`).
- Estender `editor/core/telemetria.py` com a função `enviar_relato_sentry(...)` para criar eventos com escopo isolado, anexos binários de imagens (`captura_anotada.png`) e diário de comandos, retornando o identificador único `event_id`.
- Implementar o componente gráfico `editor/views/widget_quadro_anotacao.py` (`QWidget`) para anotação livre, destaque retangular, tarja preta de privacidade e operação de desfazer (*undo*).
- Implementar o diálogo modal `editor/views/dialogos/dialogo_relato_usuario.py` com formulário de categorização, edição visual do screenshot e tarefa assíncrona de envio em segundo plano (`QThread`).
- Integrar pontos de acionamento do relato na Janela Principal (`area_principal.py` - toolbar superior e atalhos F12 / Ctrl+Shift+F), na Tela de Seleção de Croquis (`tela_de_carregamento.py`) e na Tela de Abertura/Login (`tela_de_abertura.py`).
- Garantir 100% de cobertura de testes unitários com TDD e testes de integração em português brasileiro conforme `PRINCIPIOS.md`.

**Non-Goals:**
- Gravar vídeo contínuo ou áudio da máquina do usuário.
- Enviar o relato de forma bloqueante na thread principal de interface gráfica.
- Depender de frameworks pesados de terceiros para upload HTTP multipart.

## Decisions

### 1. Tudo em Português e Nomenclatura Consistente (`PRINCIPIOS.md` - Princípio I)
- **Decisão**: Todos os arquivos, classes, funções, variáveis, testes, documentações e especificações são estritamente nomeados em português brasileiro (ex: `ColetorRelato`, `DadosDiagnostico`, `ClienteWebhookDiscord`, `WidgetQuadroAnotacao`, `DialogoRelatoUsuario`, `TarefaAssincronaEnvioRelato`).
- **Racional**: Garante consistência arquitetural e conformidade obrigatória com o Princípio I.

### 2. Arquitetura Orientada a Bibliotecas Independentes (`PRINCIPIOS.md` - Princípio II)
- **Decisão**: Toda a lógica de coleta de dados (`coletor_relato.py`), de rede (`cliente_webhook_discord.py`) e de telemetria (`telemetria.py`) é implementada em bibliotecas autossuficientes, isoladas de elementos gráficos de apresentação e testáveis individualmente.
- **Racional**: Evita acoplamento entre regras de negócio/diagnóstico e a camada de visualização do Qt.

### 3. Cliente Discord com Biblioteca Padrão e Zero Dependências Extras (`PRINCIPIOS.md` - Princípio VI)
- **Decisão**: Implementar o despachante de Webhook do Discord utilizando `urllib.request` e codificação de boundary multipart nativa.
- **Alternativas consideradas**:
  - *Usar requests/httpx*: Descartado para não adicionar dependências desnecessárias ao empacotamento PyInstaller.
  - *Usar QNetworkAccessManager*: Descartado na camada core para manter a biblioteca independente de Qt e testável com unit tests puros em Python.
- **Racional**: Simples, rápido, zero dependências externas e totalmente coberto por testes unitários com mocks de `urllib.request.urlopen`.

### 4. Integração Sentry e Ligação Direta para Discord (`editor/core/telemetria.py`)
- **Decisão**: A função `enviar_relato_sentry` usa `sentry_sdk.isolation_scope()` para anexar a imagem da captura anotada (`add_attachment(bytes=...)`), injetar tags de contexto e disparar `capture_message(..., level="info")`. O `event_id` gerado é convertido na URL do Sentry:
  `https://o4511980548849664.sentry.io/issues/?query=event.id%3A{event_id}`
  Essa URL é injetada diretamente no campo correspondente do cartão do Discord.
- **Racional**: Permite que a equipe visualize a captura de tela e discuta imediatamente no Discord, e com apenas um clique abra o Sentry para inspecionar os logs detalhados e o diário de comandos.

### 5. Quadro de Anotação e Tarja de Privacidade (`editor/views/widget_quadro_anotacao.py`)
- **Decisão**: Implementar um `QWidget` que mantém o `QPixmap` original de fundo e uma lista ordenada de comandos de traço (`TracoCaneta`, `TracoRetangulo`, `TarjaPrivacidade`). O método `paintEvent` renderiza os traços compostos com `QPainter`. Na exportação, desenha sobre uma nova `QImage` e serializa para bytes PNG.
- **Racional**: Garante desenho de alto desempenho com aceleração gráfica do Qt, suporte nativo a desfazer traços e aplicação irreversível de tarjas pretas opacas para proteção de privacidade antes da serialização.

### 6. Diálogo Modal com Despacho em QThread (`editor/views/dialogos/dialogo_relato_usuario.py`)
- **Decisão**: O diálogo executa o empacotamento da imagem e o envio de rede em uma tarefa assíncrona dedicada (`TarefaAssincronaEnvioRelato`). Enquanto o envio ocorre, os botões são desabilitados e uma barra de progresso indeterminada é exibida. Ao concluir com sucesso, o diálogo se fecha e dispara `NotificacaoToast` de confirmação.
- **Racional**: Impede qualquer congelamento visual da UI durante conexões lentas ou uploads de imagem.

### 7. Posicionamento de Acesso na Interface
- **Decisão**:
  1. `JanelaPrincipal`: Adicionar ação com ícone `Icones.obter("relato")` na `toolbar_superior` ao lado de exportar/celular, com atalhos `F12` e `Ctrl+Shift+F`.
  2. `TelaDeCarregamento`: Botão com ícone no rodapé ao lado dos botões de ação de croqui.
  3. `TelaDeAbertura`: Botão de relato no rodapé da tela.
- **Racional**: Permite ao usuário relatar problemas em qualquer estágio do ciclo de vida da aplicação.

## Risks / Trade-offs

- **[Risco] Falha de conexão de rede durante o envio** → *Mitigação*: O worker captura exceções de rede e emite sinal de erro para o diálogo, exibindo alerta claro e mantendo o formulário aberto para nova tentativa sem perda dos dados digitados.
- **[Risco] Envio de imagens com dados confidenciais** → *Mitigação*: Disponibilização em destaque da ferramenta de "Tarja de Privacidade" (preto opaco) e sanitização automática de caminhos no texto descritivo via `sanitizar_texto_caminhos`.
- **[Risco] Ausência ou expiração da URL do Webhook do Discord** → *Mitigação*: A URL do webhook pode ser configurada via variável de ambiente (`ARESTA_DISCORD_FEEDBACK_WEBHOOK`) com fallback para URL padrão; caso não esteja configurada ou o Discord falhe, o envio ao Sentry prossegue normalmente.
