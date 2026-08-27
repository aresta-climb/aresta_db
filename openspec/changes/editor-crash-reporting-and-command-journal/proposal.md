## Why

Atualmente, quando o Editor Aresta sofre uma exceção não tratada em ambiente Windows (compilado com `--windowed`), a aplicação fecha silenciosamente sem deixar rastros para o usuário comum e sem notificar os desenvolvedores. Além disso, se ocorrer um encerramento inesperado ou falta de energia durante a edição de um croqui, o progresso não salvo é perdido, e o histórico de ações (`QUndoStack`) é descartado entre sessões.

Esta mudança introduz telemetria automática e silenciosa de falhas via Sentry, um sistema transacional de journaling de comandos (`QUndoCommand`) com preservação de estado e imagens em formato WebP dummy redigido, capacidade de recuperação de desastres (autosave / crash recovery) e a formalização da Política de Privacidade do projeto.

## What Changes

- **Telemetria Silenciosa de Crashes com Sentry**: Inicialização do `sentry-sdk` capturando `sys.excepthook`, `threading.excepthook` e breadcrumbs estruturados a partir das ações do usuário.
- **Sanitização de Dados (PII & Paths)**: Interceptador `before_send` que higieniza caminhos locais (substituindo nomes de usuário do Windows por `%APPDATA%`, `%USERPROFILE%`), remove tokens do GitHub e credenciais sensíveis antes do envio.
- **Dummy WebP com Dimensões Preservadas (`redacted=True`)**: Helper para gerar imagens WebP homogêneas de tamanho ínfimo (< 100 bytes) preservando `width` e `height` originais para payloads de crash reports minúsculos e privados.
- **Rastreamento de Commit Base**: Adição do campo `commit_base_sha` na mensagem Protobuf `CroquiExperimental` para vincular a raiz da edição ao commit original do repositório `aresta_db`.
- **Serialização e Deserialização de `QUndoCommand`s**: Implementação de métodos `serializar(redacted=False)` e `deserializar(dados, model)` para todos os comandos de histórico do editor.
- **Journaling Transacional de Comandos**: Separação do histórico em disco entre `journal_salvo.bin` (comandos consolidados após Salvar) e `journal_pendente.bin` (ações da sessão corrente) utilizando `pickle` append-only de alta performance.
- **Recuperação de Desastres (Crash Recovery / Autosave)**: Diálogo na inicialização que detecta encerramento anômalo e oferece ao usuário as opções de "Recuperar Trabalho" (replay dos comandos com restauração da `QUndoStack`) ou "Descartar" (limpeza do journal pendente).
- **Migração de `print` para Logging Estruturado**: Substituição de chamadas diretas a `print(...)` no módulo `editor/` pelo `logging` padrão integrado aos breadcrumbs do Sentry e com gravação em `%APPDATA%/editor_aresta/logs/editor.log`.
- **Política de Privacidade**: Criação formal do documento `PRIVACIDADE.md` detalhando a coleta anônima de telemetria de erros, sanitização de dados e compromisso de privacidade.

## Capabilities

### New Capabilities
- `editor-telemetria-crash`: Sistema de monitoramento e telemetria de erros com Sentry, captura global de exceções, sanitização de dados em `before_send` e geração de imagens WebP dummy redigidas.
- `editor-journal-recuperacao`: Sistema transacional de journaling de comandos em disco (`journal_salvo.bin` e `journal_pendente.bin`), recuperação de sessão após encerramento anômalo e restauração de `QUndoStack`.

### Modified Capabilities
- `croqui-experimental-format`: Adição do campo `commit_base_sha` no protobuf `CroquiExperimental` para registrar o SHA do commit base do `aresta_db`.
- `undo-redo-global`: Requisito de serialização (`serializar(redacted=...)`) e deserialização (`deserializar(...)`) para todos os `QUndoCommand`s do editor.

## Impact

- **Dependências**: Adição de `sentry-sdk` ao `requirements.txt` do editor e configuração de empacotamento no PyInstaller (`editor/build.py`).
- **Protobuf**: Atualização de `aresta_api/proto/croqui_experimental.proto` e recompilação dos stubs Python.
- **Core do Editor**: Novos módulos `editor/core/telemetry.py`, `editor/core/journal.py`, `editor/core/logger.py` e refatoração em `editor/core/historico.py`, `editor/core/croqui_experimental.py`, `editor/core/workspace.py` e `editor/main.py`.
- **Documentação**: Adição do arquivo `PRIVACIDADE.md` na raiz do repositório.
