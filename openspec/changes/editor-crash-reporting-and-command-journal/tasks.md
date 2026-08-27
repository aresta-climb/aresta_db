## 1. Protobuf e Metadados do Croqui Experimental

- [ ] 1.1 Adicionar o campo `string commit_base_sha = 9;` ao protobuf `CroquiExperimental` em `aresta_api/proto/croqui_experimental.proto`
- [ ] 1.2 Recompilar os arquivos gerados de protobuf (`aresta_api/proto/generated/`)
- [ ] 1.3 Atualizar `GerenciadorCroquiExperimental` para capturar e persistir o `commit_base_sha` do repositório base `aresta_db` na criação a partir de oficial
- [ ] 1.4 Adicionar testes unitários para a persistência e leitura de `commit_base_sha` em `editor/core/croqui_experimental_test.py`

## 2. Helper de Dummy WebP e Serialização de Comandos (QUndoCommand)

- [ ] 2.1 Criar a biblioteca utilitária `editor/core/imagem_dummy.py` com a função `gerar_dummy_webp(img_bytes)` preservando dimensões originais e compressão extrema
- [ ] 2.2 Adicionar testes unitários completos em `editor/core/imagem_dummy_test.py` validando formatos PNG, JPEG, RGBA, dimensões e limites de tamanho (< 150 bytes)
- [ ] 2.3 Implementar métodos `serializar(redacted: bool = False)` e `deserializar(dados, model)` nos comandos de `editor/commands/comandos_protobuf.py`
- [ ] 2.4 Implementar métodos `serializar(redacted: bool = False)` e `deserializar(dados, model)` nos comandos de `editor/commands/comandos_mapas.py`
- [ ] 2.5 Criar testes unitários para serialização/deserialização (com e sem `redacted=True`) em `editor/commands/comandos_protobuf_test.py` e `editor/commands/comandos_mapas_test.py`

## 3. Biblioteca de Journaling Transacional em Disco

- [ ] 3.1 Criar a biblioteca `editor/core/journal.py` (`GerenciadorJournal`) gerenciando `journal_pendente.bin` e `journal_salvo.bin` com `pickle` append-only
- [ ] 3.2 Implementar método de consolidação (transferência de pendente para salvo e truncagem do pendente) no `GerenciadorJournal`
- [ ] 3.3 Implementar leitura resiliente do journal com tratamento de final de arquivo corrompido (`EOFError`)
- [ ] 3.4 Implementar geração do pacote de telemetria redigido (`exportar_journal_redacted()`)
- [ ] 3.5 Adicionar 100% de cobertura de testes unitários em `editor/core/journal_test.py`

## 4. Integração do Journal com o Histórico e Workspace

- [ ] 4.1 Conectar o `GerenciadorHistorico` (`editor/core/historico.py`) ao `GerenciadorJournal` para gravar automaticamente cada comando executado
- [ ] 4.2 Integrar o `ExperimentalWorkspace` (`editor/core/workspace.py`) com o `GerenciadorJournal` para consolidar o histórico durante o salvamento/build
- [ ] 4.3 Implementar método de replay do histórico no `GerenciadorHistorico` para reconstruir o estado e a pilha de Undo/Redo a partir de um journal
- [ ] 4.4 Adicionar testes de integração em `editor/core/historico_test.py` e `editor/core/workspace_test.py`

## 5. Interface de Recuperação de Sessão (Crash Recovery)

- [ ] 5.1 Criar o diálogo modal `editor/views/dialogo_recuperacao_sessao.py` exibindo informações sobre alterações não salvas detectadas
- [ ] 5.2 Conectar os botões "Recuperar Trabalho" e "Descartar" à lógica do `GerenciadorJournal` na inicialização do croqui
- [ ] 5.3 Adicionar testes unitários da interface e sinais em `editor/views/dialogo_recuperacao_sessao_test.py`

## 6. Telemetria Sentry e Sanitização de Dados

- [ ] 6.1 Adicionar dependência `sentry-sdk` em `requirements.txt` e `editor/requirements.txt`, atualizando configuração do PyInstaller em `editor/build.py`
- [ ] 6.2 Criar módulo `editor/core/telemetry.py` com inicialização do Sentry, DSN do projeto e captura global de `sys.excepthook` e `threading.excepthook`
- [ ] 6.3 Implementar o interceptador `before_send` em `telemetry.py` para sanitização universal de caminhos de arquivos e expurgo de tokens
- [ ] 6.4 Integrar anexo do journal redigido (`exportar_journal_redacted()`) e breadcrumbs da `QUndoStack` ao payload do Sentry no momento de um crash
- [ ] 6.5 Adicionar 100% de testes unitários em `editor/core/telemetry_test.py` com mocks do SDK do Sentry

## 7. Migração de Logging e Rotação de Logs Locais

- [ ] 7.1 Criar biblioteca `editor/core/logger.py` configurando logging estruturado com saída para console, arquivo rotativo `%APPDATA%/editor_aresta/logs/editor.log` e Sentry breadcrumbs
- [ ] 7.2 Substituir chamadas a `print(...)` em `editor/main.py`, `editor/core/worker.py`, `editor/core/workspace.py` e demais controladores por `logger.info`, `logger.debug` e `logger.error`
- [ ] 7.3 Adicionar testes unitários em `editor/core/logger_test.py` validando rotação de arquivos e formatação

## 8. Documentação e Política de Privacidade

- [ ] 8.1 Criar o documento `PRIVACIDADE.md` na raiz do repositório detalhando a política de privacidade, coleta anônima de telemetria e sanitização de dados
- [ ] 8.2 Atualizar `README.md` e `GUIA_DO_DESENVOLVEDOR.md` com instruções de configuração da telemetria e recuperação de histórico
