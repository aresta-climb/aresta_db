## Why

Atualmente, quando o Editor Aresta sofre uma exceção não tratada em ambiente Windows (compilado com `--windowed`), a aplicação encerra silenciosamente sem deixar registros acessíveis ao usuário comum e sem notificar os desenvolvedores. Além disso, caso ocorra um encerramento inesperado ou falta de energia durante a edição de um croqui, o trabalho não salvo é perdido, e o histórico de ações (`QUndoStack`) é descartado entre sessões.

Esta mudança introduz telemetria automática e silenciosa de falhas via Sentry, um sistema transacional de diário de comandos (`QUndoCommand`) com preservação de estado e imagens em formato WebP anonimizado, capacidade de recuperação de desastres (autosave / recuperação de sessão) e a atualização formal da Política de Privacidade do Editor em `../arestaclimb.com/public/docs/politica-de-privacidade-editor.md`.

## What Changes

- **Telemetria Silenciosa de Falhas com Sentry**: Inicialização do `sentry-sdk` capturando `sys.excepthook`, `threading.excepthook` e breadcrumbs estruturados a partir das ações do usuário.
- **Sanitização Universal de Dados (Privacidade e Nomes de Usuário)**: Interceptador `before_send` que higieniza caminhos locais (substituindo caminhos do Windows por `%APPDATA%`, `%LOCALAPPDATA%`, `%USERPROFILE%`), remove tokens do GitHub e credenciais sensíveis antes de qualquer envio externo.
- **WebP Anonimizado com Dimensões Preservadas (`anonimizado=True`)**: Biblioteca utilitária para gerar imagens WebP homogêneas de tamanho ínfimo (< 150 bytes) preservando a largura (`width`) e altura (`height`) originais para compor pacotes de diagnóstico leves e privados.
- **Rastreamento de Commit Base (`commit_base_sha`)**: Adição do campo `commit_base_sha` na mensagem Protobuf `CroquiExperimental` para vincular a raiz da edição ao commit original do repositório `aresta_db`.
- **Serialização e Deserialização de `QUndoCommand`s**: Implementação dos métodos `serializar(anonimizado: bool = False)` e `deserializar(dados: dict, model: CroquiModel)` para todos os comandos de histórico do editor.
- **Diário Transacional de Comandos em Disco**: Separação do histórico em arquivos binários append-only de alta performance: `diario_salvo.bin` (comandos consolidados após salvamento) e `diario_pendente.bin` (ações da sessão corrente) utilizando `pickle`.
- **Recuperação de Desastres (Autosave / Recuperação de Sessão)**: Diálogo modal na inicialização que detecta encerramento anômalo e oferece ao usuário as opções de "Recuperar Trabalho" (execução ordenada dos comandos com restauração da `QUndoStack`) ou "Descartar" (limpeza do diário pendente).
- **Migração de `print` para Logging Estruturado**: Substituição de chamadas diretas a `print(...)` no módulo `editor/` pelo `logging` padrão em português brasileiro, integrado aos breadcrumbs do Sentry e com gravação em arquivo rotativo `%APPDATA%/editor_aresta/logs/editor.log`.
- **Atualização da Política de Privacidade**: Atualização de `../arestaclimb.com/public/docs/politica-de-privacidade-editor.md`, detalhando a telemetria técnica de estabilidade via Sentry, a anonimização de caminhos locais e a garantia de não envio de fotos/mídias pessoais.

## Capabilities

### New Capabilities
- `editor-telemetria-crash`: Sistema de monitoramento e telemetria de erros com Sentry, captura global de exceções, sanitização de dados no interceptador `before_send` e geração de imagens WebP anonimizadas.
- `editor-diario-recuperacao`: Sistema transacional de diário de comandos em disco (`diario_salvo.bin` e `diario_pendente.bin`), recuperação de sessão após encerramento anômalo e restauração da pilha `QUndoStack`.

### Modified Capabilities
- `croqui-experimental-format`: Adição do campo `commit_base_sha` no protobuf `CroquiExperimental` para registrar o hash SHA do commit base do `aresta_db`.
- `undo-redo-global`: Requisito de serialização (`serializar(anonimizado=...)`) e deserialização (`deserializar(...)`) para todos os `QUndoCommand`s do editor.

## Impact

- **Dependências**: Adição de `sentry-sdk` ao `requirements.txt` do editor e configuração de empacotamento no PyInstaller (`editor/build.py`).
- **Protobuf**: Atualização de `aresta_api/proto/croqui_experimental.proto` e recompilação dos stubs Python.
- **Core do Editor**: Criação das bibliotecas `editor/core/telemetria.py`, `editor/core/diario.py`, `editor/core/registro_log.py`, `editor/core/imagem_anonimizada.py` e refatoração em `editor/core/historico.py`, `editor/core/croqui_experimental.py`, `editor/core/workspace.py` e `editor/main.py`.
- **Views**: Criação do diálogo `editor/views/dialogo_recuperacao_sessao.py`.
- **Documentação e Web**: Atualização de `../arestaclimb.com/public/docs/politica-de-privacidade-editor.md`.

## Engineering Principles

- **I. Tudo em Português**: Todo o código, módulos (`telemetria.py`, `diario.py`, `registro_log.py`, `imagem_anonimizada.py`), nomes de métodos (`serializar`, `deserializar`, `gerar_webp_anonimizado`), variáveis, comentários e documentações são estritamente em português brasileiro.
- **II. Library-First**: Cada funcionalidade é construída como uma biblioteca independente, autossuficiente e testável (`editor/core/imagem_anonimizada.py`, `editor/core/diario.py`, `editor/core/telemetria.py`, `editor/core/registro_log.py`).
- **III. 100% Unit Test Coverage**: Todos os arquivos `.py` implementados possuem 100% de cobertura de testes unitários.
- **IV. TDD (Test-Driven Development)**: Os testes (`_test.py`) correspondentes são escritos e validados antes da implementação do código de produção para cada módulo e comando.
- **V. Testes de Integração em Primeiro Lugar**: Estabelecidos testes de fronteira integrando o `GerenciadorHistorico`, `GerenciadorDiario`, `CroquiModel` e `ExperimentalWorkspace`.
- **VI. Simplicidade e Anti-Abstração**: Estrutura direta com arquivos binários append-only (`pickle`), sem frameworks intermediários complexos ou abstrações prematuras.
- **VII. Edições de Estado via Comandos do Histórico**: A recuperação de sessão e replay de estado utilizam a execução sequencial nativa dos `QUndoCommand`s na pilha global do `GerenciadorHistorico`.
