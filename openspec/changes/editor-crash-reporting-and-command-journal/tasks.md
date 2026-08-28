## 1. Protobuf e Metadados do Croqui Experimental

- [x] 1.1 Adicionar o campo `string commit_base_sha = 9;` ao protobuf `CroquiExperimental` em `aresta_api/proto/croqui_experimental.proto`
- [x] 1.2 Recompilar os arquivos gerados de protobuf (`aresta_api/proto/generated/`)
- [x] 1.3 Escrever testes unitários em `editor/core/croqui_experimental_test.py` para a persistência e leitura de `commit_base_sha`
- [x] 1.4 Atualizar `GerenciadorCroquiExperimental` para capturar e persistir o `commit_base_sha` do repositório base `aresta_db` na criação a partir de oficial

## 2. Biblioteca de Imagem Anonimizada e Serialização de Comandos (QUndoCommand)

- [x] 2.1 Criar testes unitários em `editor/core/imagem_anonimizada_test.py` validando formatos PNG, JPEG, RGBA, dimensões e limites de tamanho (< 150 bytes)
- [x] 2.2 Criar a biblioteca utilitária `editor/core/imagem_anonimizada.py` com a função `gerar_webp_anonimizado(img_bytes)`
- [x] 2.3 Escrever testes unitários para serialização e deserialização em `editor/commands/comandos_protobuf_test.py` (com e sem `anonimizado=True`)
- [x] 2.4 Implementar métodos `serializar(anonimizado: bool = False)` e `deserializar(dados, model)` nos comandos de `editor/commands/comandos_protobuf.py`
- [x] 2.5 Escrever testes unitários para serialização e deserialização em `editor/commands/comandos_mapas_test.py` (com e sem `anonimizado=True`)
- [x] 2.6 Implementar métodos `serializar(anonimizado: bool = False)` e `deserializar(dados, model)` nos comandos de `editor/commands/comandos_mapas.py`

## 3. Biblioteca de Diário Transacional em Disco (GerenciadorDiario)

- [x] 3.1 Criar testes unitários em `editor/core/diario_test.py` cobrindo gravação append-only, consolidação, truncagem, leitura resiliente com `EOFError` e exportação anonimizada
- [x] 3.2 Implementar a biblioteca `editor/core/diario.py` (`GerenciadorDiario`) gerenciando `diario_pendente.bin` e `diario_salvo.bin` com `pickle` append-only
- [x] 3.3 Implementar método de consolidação (transferência de pendente para salvo e truncagem do pendente) no `GerenciadorDiario`
- [x] 3.4 Implementar leitura resiliente do diário com tratamento de final de arquivo corrompido (`EOFError`)
- [x] 3.5 Implementar geração do pacote de telemetria anonimizado (`exportar_diario_anonimizado()`)

## 4. Integração do Diário com o Histórico e Workspace

- [x] 4.1 Criar testes de integração em `editor/core/historico_test.py` e `editor/core/workspace_test.py` para sincronização com o diário e replay de comandos
- [x] 4.2 Conectar o `GerenciadorHistorico` (`editor/core/historico.py`) ao `GerenciadorDiario` para persistir automaticamente cada comando executado
- [x] 4.3 Integrar o `ExperimentalWorkspace` (`editor/core/workspace.py`) com o `GerenciadorDiario` para consolidar o histórico durante o salvamento e compilação
- [x] 4.4 Implementar método de replay do histórico no `GerenciadorHistorico` para reconstruir o estado e a pilha `QUndoStack` a partir de um diário

## 5. Interface de Recuperação de Sessão (Crash Recovery)

- [x] 5.1 Criar testes de interface com `pytest-qt` em `editor/views/dialogo_recuperacao_sessao_test.py`
- [x] 5.2 Implementar o diálogo de recuperação `editor/views/dialogo_recuperacao_sessao.py` (`DialogoRecuperacaoSessao`) com opções de Recuperar Trabalho e Descartar
- [x] 5.3 Conectar a verificação de `diario_pendente.bin` no fluxo de abertura do croqui (`editor/views/janela_principal.py` / `editor/controllers/croqui_controller.py`)

## 6. Biblioteca de Telemetria Sentry e Sanitização Universal

- [x] 6.1 Criar testes unitários em `editor/core/telemetria_test.py` cobrindo sanitização de paths com `%appdata%` e `%userprofile%`, anexos de diário e inicialização silenciosa
- [x] 6.2 Implementar a biblioteca `editor/core/telemetria.py` inicializando `sentry_sdk` com DSN oficial, silencioso e sem prompts
- [x] 6.3 Configurar hook `before_send` para sanitização universal de paths locais nos eventos e exceções
- [x] 6.4 Configurar hooks `sys.excepthook` e `threading.excepthook` para capturar exceções não tratadas e anexar o histórico anonimizado ao crash report
- [x] 6.5 Inicializar a telemetria no ponto de entrada `editor/main.py`

## 7. Biblioteca de Logging Estruturado e Rotação de Logs

- [x] 7.1 Criar testes unitários em `editor/core/registro_log_test.py` cobrindo níveis de log, rotação de 3 arquivos de 5MB e sanitização
- [x] 7.2 Implementar a biblioteca `editor/core/registro_log.py` com `RotatingFileHandler` em `%appdata%/ArestaEditor/logs/` e integração com Sentry
- [x] 7.3 Substituir chamadas a `print(...)` em `editor/main.py`, `editor/core/worker.py`, `editor/core/workspace.py` e controladores por chamadas a `logger.info`, `logger.debug` e `logger.error`

## 8. Documentação e Política de Privacidade

- [x] 8.1 Atualizar `c:\Renato\Devel\aresta-climb\arestaclimb.com\public\docs\politica-de-privacidade-editor.md` com a cláusula de telemetria silenciosa e sanitização
- [x] 8.2 Documentar o sistema de telemetria e o diário transacional em `GUIA_DO_DESENVOLVEDOR.md` e `README.md`
- [x] 8.3 Executar bateria completa de testes unitários e de integração garantindo 100% de sucesso
