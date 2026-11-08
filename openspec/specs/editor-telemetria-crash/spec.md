# editor-telemetria-crash Specification

## Purpose
Prover telemetria silenciosa de falhas e diagnósticos de sessão para o Editor Aresta via Sentry, incluindo sanitização de dados pessoais e caminhos locais, registro cronológico de breadcrumbs de comandos e logs, anexação do diário transacional e integração contínua com campanhas do Robô Caótico.

## Requirements

### Requirement: Inicialização da Telemetria e Captura Global de Erros
O Editor Aresta SHALL prover a biblioteca `editor/core/telemetria.py` para inicializar o cliente Sentry de forma leve no ciclo de vida da aplicação (`editor/main.py`), desativando a detecção e ativação automática de integrações com bibliotecas de terceiros (`auto_enabling_integrations=False`), e capturar de forma global e silenciosa quaisquer exceções não tratadas disparadas na thread principal (`sys.excepthook`) e em threads secundárias (`threading.excepthook`).

#### Scenario: Exceção não tratada na interface gráfica
- **WHEN** uma exceção não tratada é disparada em um callback ou slot do PyQt6
- **THEN** o interceptador global captura a exceção, registra os detalhes no log local e submete o evento de erro ao Sentry com `sentry_sdk.flush()`.

#### Scenario: Exceção em thread de sincronização em segundo plano
- **WHEN** uma thread de background (worker) sofre uma falha fatal não capturada
- **THEN** o `threading.excepthook` intercepta o erro e submete o relatório de diagnóstico ao Sentry.

#### Scenario: Inicialização rápida sem auto-integrações externas
- **WHEN** a função de inicialização da telemetria for executada no arranque da aplicação
- **THEN** o cliente Sentry SHALL ser inicializado com `auto_enabling_integrations=False`
- **THEN** o tempo gasto na inicialização do Sentry não SHALL bloquear a inicialização ou renderização da interface gráfica.

### Requirement: Sanitização de Dados Sensíveis e Nomes de Usuário (PII)
O sistema SHALL sanitizar todos os eventos e breadcrumbs antes do envio ao Sentry através do interceptador `before_send`, substituindo caminhos absolutos do sistema operacional contendo nomes de usuários por `%APPDATA%`, `%LOCALAPPDATA%` ou `%USERPROFILE%` (suportando tanto barras simples normais/invertidas quanto barras duplas escapadas em strings serializadas), e removendo quaisquer tokens de autenticação ou credenciais sensíveis.

#### Scenario: Sanitização de caminhos no Windows
- **WHEN** uma mensagem de log ou stack trace contém o caminho `C:\Users\joaosilva\AppData\Roaming\editor_aresta\croquis\setor.yaml`
- **THEN** o interceptador `before_send` substitui o trecho pelo caminho sanitizado `%APPDATA%\editor_aresta\croquis\setor.yaml` antes de realizar o envio.

#### Scenario: Sanitização de caminhos com barras duplas escapadas
- **WHEN** uma mensagem de erro contém caminhos serializados via `repr()`, listas, tuplas ou exceções (ex: `C:\\Users\\joaosilva\\AppData\\Local\\Packages\\...`)
- **THEN** o interceptador `before_send` substitui o trecho escapado pelo identificador sanitizado correspondente (`%LOCALAPPDATA%\\Packages\\...`) sem vazar o nome de usuário local.

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

### Requirement: Envio de Receita do Robô Caótico no Contexto do Sentry
A biblioteca `editor/core/telemetria.py` SHALL manter o cliente Sentry continuamente ativo durante toda a campanha do Robô Caótico (registrando em tempo real os *breadcrumbs* de comandos do histórico e logs da aplicação) e, ao reportar uma falha inédita encontrada pelo robô, SHALL definir nível de severidade `fatal`, anexar o contexto estruturado `contexts.receita_robo_caotico` e anexar o arquivo `.json` da receita (`content_type="application/json"`) ao escopo do evento enviado ao Sentry.

#### Scenario: Captura de falha inédita encontrada pelo Robô Caótico
- **WHEN** o motor do Robô Caótico executa uma campanha com o envio ao Sentry habilitado e uma semente sofre uma falha inédita
- **THEN** o evento enviado ao Sentry SHALL conter o *stacktrace* real da exceção, todos os *breadcrumbs* cronológicos registrados durante os passos daquela semente até o momento da falha, `level="fatal"`, a tag `origem_crash="robo_caotico"`, o contexto estruturado `contexts.receita_robo_caotico` e o arquivo `.json` completo da receita anexado ao evento.

### Requirement: Diagnóstico e Reprodução de Receitas do Editor via MCP Sentry
A skill `diagnosticar-issue-sentry` SHALL documentar o fluxo de extração de `contexts.receita_robo_caotico` para issues do `aresta_db`, orientando o salvamento da receita em `editor/caos/caminhos_regressao/` e sua execução via `pytest editor/caos/regressao_caminhos_test.py`.

#### Scenario: Reprodução de issue do Editor Aresta gerada pelo Robô Caótico
- **WHEN** um agente investiga uma Issue do GitHub do `aresta_db` vinculada a um evento do Sentry que possui `contexts.receita_robo_caotico`
- **THEN** o agente SHALL salvar o JSON da receita em `editor/caos/caminhos_regressao/issue_<NUMERO>_seed_<SEED>.json` e reproduzir a falha executando `uv run pytest editor/caos/regressao_caminhos_test.py` antes de aplicar a correção.
