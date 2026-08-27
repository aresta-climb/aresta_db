## 1. Protobuf e Metadados do Croqui Experimental

- [ ] 1.1 Adicionar o campo `string commit_base_sha = 9;` ao protobuf `CroquiExperimental` em `aresta_api/proto/croqui_experimental.proto`
- [ ] 1.2 Recompilar os arquivos gerados de protobuf (`aresta_api/proto/generated/`)
- [ ] 1.3 Escrever testes unitários em `editor/core/croqui_experimental_test.py` para a persistência e leitura de `commit_base_sha`
- [ ] 1.4 Atualizar `GerenciadorCroquiExperimental` para capturar e persistir o `commit_base_sha` do repositório base `aresta_db` na criação a partir de oficial

## 2. Biblioteca de Imagem Anonimizada e Serialização de Comandos (QUndoCommand)

- [ ] 2.1 Criar testes unitários em `editor/core/imagem_anonimizada_test.py` validando formatos PNG, JPEG, RGBA, dimensões e limites de tamanho (< 150 bytes)
- [ ] 2.2 Criar a biblioteca utilitária `editor/core/imagem_anonimizada.py` com a função `gerar_webp_anonimizado(img_bytes)`
- [ ] 2.3 Escrever testes unitários para serialização e deserialização em `editor/commands/comandos_protobuf_test.py` (com e sem `anonimizado=True`)
- [ ] 2.4 Implementar métodos `serializar(anonimizado: bool = False)` e `deserializar(dados, model)` nos comandos de `editor/commands/comandos_protobuf.py`
- [ ] 2.5 Escrever testes unitários para serialização e deserialização em `editor/commands/comandos_mapas_test.py` (com e sem `anonimizado=True`)
- [ ] 2.6 Implementar métodos `serializar(anonimizado: bool = False)` e `deserializar(dados, model)` nos comandos de `editor/commands/comandos_mapas.py`

## 3. Biblioteca de Diário Transacional em Disco (GerenciadorDiario)

- [ ] 3.1 Criar testes unitários em `editor/core/diario_test.py` cobrindo gravação append-only, consolidação, truncagem, leitura resiliente com `EOFError` e exportação anonimizada
- [ ] 3.2 Implementar a biblioteca `editor/core/diario.py` (`GerenciadorDiario`) gerenciando `diario_pendente.bin` e `diario_salvo.bin` com `pickle` append-only
- [ ] 3.3 Implementar método de consolidação (transferência de pendente para salvo e truncagem do pendente) no `GerenciadorDiario`
- [ ] 3.4 Implementar leitura resiliente do diário com tratamento de final de arquivo corrompido (`EOFError`)
- [ ] 3.5 Implementar geração do pacote de telemetria anonimizado (`exportar_diario_anonimizado()`)

## 4. Integração do Diário com o Histórico e Workspace

- [ ] 4.1 Criar testes de integração em `editor/core/historico_test.py` e `editor/core/workspace_test.py` para sincronização com o diário e replay de comandos
- [ ] 4.2 Conectar o `GerenciadorHistorico` (`editor/core/historico.py`) ao `GerenciadorDiario` para persistir automaticamente cada comando executado
- [ ] 4.3 Integrar o `ExperimentalWorkspace` (`editor/core/workspace.py`) com o `GerenciadorDiario` para consolidar o histórico durante o salvamento e compilação
- [ ] 4.4 Implementar método de replay do histórico no `GerenciadorHistorico` para reconstruir o estado e a pilha `QUndoStack` a partir de um diário

## 5. Interface de Recuperação de Sessão (Crash Recovery)

- [ ] 5.1 Criar testes unitários e de interface em `editor/views/dialogo_recuperacao_sessao_test.py` validando emissão de sinais e botões de ação
- [ ] 5.2 Implementar o diálogo modal `editor/views/dialogo_recuperacao_sessao.py` exibindo informações sobre alterações não salvas detectadas
- [ ] 5.3 Conectar os fluxos de "Recuperar Trabalho" e "Descartar" à inicialização do croqui na `TelaDeCarregamento` e `JanelaPrincipal`

## 6. Biblioteca de Telemetria Sentry e Sanitização Universal

- [ ] 6.1 Adicionar dependência `sentry-sdk` em `requirements.txt` e `editor/requirements.txt`, atualizando configuração do PyInstaller em `editor/build.py`
- [ ] 6.2 Criar testes unitários em `editor/core/telemetria_test.py` com mocks do SDK do Sentry validando captura de hooks globais, sanitização de caminhos e ocultação de tokens
- [ ] 6.3 Implementar a biblioteca `editor/core/telemetria.py` com inicialização do Sentry, interceptador `before_send` para sanitização e captura global de `sys.excepthook` e `threading.excepthook`
- [ ] 6.4 Integrar anexo do diário anonimizado (`exportar_diario_anonimizado()`) e breadcrumbs da `QUndoStack` ao payload do Sentry no momento de um erro fatal
- [ ] 6.5 Inicializar a telemetria no início do ponto de entrada `editor/main.py`

## 7. Biblioteca de Logging Estruturado e Rotação de Logs

- [ ] 7.1 Criar testes unitários em `editor/core/registro_log_test.py` validando formatação em português, rotação de arquivos e envio para breadcrumbs
- [ ] 7.2 Implementar a biblioteca `editor/core/registro_log.py` configurando logging estruturado com saída para console, arquivo rotativo `%APPDATA%/editor_aresta/logs/editor.log` e Sentry
- [ ] 7.3 Substituir chamadas a `print(...)` em `editor/main.py`, `editor/core/worker.py`, `editor/core/workspace.py` e controladores por chamadas a `logger.info`, `logger.debug` e `logger.error`

## 8. Documentação e Política de Privacidade

- [ ] 8.1 Atualizar a Política de Privacidade do Editor em `../arestaclimb.com/public/docs/politica-de-privacidade-editor.md`, incluindo a seção de telemetria técnica de falhas (Sentry), sanitização de caminhos locais e compromisso de não envio de mídias/fotos pessoais
- [ ] 8.2 Atualizar `README.md` e `GUIA_DO_DESENVOLVEDOR.md` com instruções sobre a telemetria, recuperação de sessão e boas práticas de diário de comandos
