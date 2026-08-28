## ADDED Requirements

### Requirement: Inicialização da Telemetria e Captura Global de Erros
O Editor Aresta SHALL prover a biblioteca `editor/core/telemetria.py` para inicializar o cliente Sentry no início do ciclo de vida da aplicação (`editor/main.py`) e capturar de forma global e silenciosa quaisquer exceções não tratadas disparadas na thread principal (`sys.excepthook`) e em threads secundárias (`threading.excepthook`).

#### Scenario: Exceção não tratada na interface gráfica
- **WHEN** uma exceção não tratada é disparada em um callback ou slot do PyQt6
- **THEN** o interceptador global captura a exceção, registra os detalhes no log local e submete o evento de erro ao Sentry com `sentry_sdk.flush()`.

#### Scenario: Exceção em thread de sincronização em segundo plano
- **WHEN** uma thread de background (worker) sofre uma falha fatal não capturada
- **THEN** o `threading.excepthook` intercepta o erro e submete o relatório de diagnóstico ao Sentry.

### Requirement: Sanitização de Dados Sensíveis e Nomes de Usuário (PII)
O sistema SHALL sanitizar todos os eventos e breadcrumbs antes do envio ao Sentry através do interceptador `before_send`, substituindo caminhos absolutos do sistema operacional contendo nomes de usuários por `%APPDATA%`, `%LOCALAPPDATA%` ou `%USERPROFILE%`, e removendo quaisquer tokens de autenticação ou credenciais sensíveis.

#### Scenario: Sanitização de caminhos no Windows
- **WHEN** uma mensagem de log ou stack trace contém o caminho `C:\Users\joaosilva\AppData\Roaming\editor_aresta\croquis\setor.yaml`
- **THEN** o interceptador `before_send` substitui o trecho pelo caminho sanitizado `%APPDATA%\editor_aresta\croquis\setor.yaml` antes de realizar o envio.

#### Scenario: Sanitização de tokens de autenticação
- **WHEN** um token do GitHub (`ghp_...` ou `gho_...`) estiver presente no contexto do erro
- **THEN** o token é substituído por `[TOKEN_OCULTADO]` antes do envio.

### Requirement: Geração de Imagem WebP Anonimizada
O sistema SHALL prover a biblioteca utilitária `editor/core/imagem_anonimizada.py` com a função `gerar_webp_anonimizado(img_bytes)` que, para qualquer buffer de imagem válido, gere uma imagem WebP composta por pixels homogêneos mantendo rigorosamente a largura (`width`) e a altura (`height`) originais, atingindo tamanho inferior a 150 bytes.

#### Scenario: Anonimização de imagem para anexo de telemetria
- **WHEN** um comando contendo uma fotografia de alta resolução (ex: 4000x3000 pixels e 8 MB) é preparado para envio de telemetria (`anonimizado=True`)
- **THEN** a imagem é convertida em um WebP anonimizado de 4000x3000 pixels com tamanho inferior a 150 bytes, sem transferir o conteúdo visual original do usuário.

### Requirement: Logging Estruturado Integrado
O módulo `editor/` SHALL utilizar a biblioteca `editor/core/registro_log.py`, enviando registros para a saída padrão em ambiente de desenvolvimento, para o arquivo `%APPDATA%/editor_aresta/logs/editor.log` (com rotação) e alimentando automaticamente os breadcrumbs do Sentry.

#### Scenario: Registro de ações do usuário em breadcrumbs
- **WHEN** o editor executa `logger.info("Sincronização iniciada com branch %s", branch)`
- **THEN** a mensagem é gravada no arquivo de log local e adicionada à linha do tempo de breadcrumbs da sessão no Sentry.
