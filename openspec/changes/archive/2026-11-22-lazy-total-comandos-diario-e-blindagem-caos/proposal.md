# Proposal

## Why

A Issue #103 (`ARESTA-EDITOR-T`) expôs que, ao abrir um croqui com histórico persistido em `diario_salvo.bin`, a deserialização de comandos (`CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated` e comandos legados) ainda realizava consultas ansiosas à árvore Protobuf atual (`_obter_msg()`, `_validar_campo_se_msg_existir()`, leitura de buffers em memória e geração de `UID`), disparando dezenas de erros falsos-positivos no Sentry quando passos intermediários do histórico referenciavam caminhos ou variantes `oneof` já transformados no estado final do croqui. Além disso, quatro lacunas na suíte de testes e no Robô Caótico (namespace de logger desconectado do Oráculo 1, validação rasa apenas de `pickle` no Oráculo 3, ausência de ação de reabertura de sessão e ausência de invalidação de diários após migrações de schema) impediram que essa regressão e a perda de estado de `oneof` pós-reabertura fossem detectadas antes da produção.

## What Changes

- **Deserialização 100% Pura e *Lazy* em Todos os Comandos**: Todos os 7 comandos canônicos (`editor/commands/comandos_protobuf.py`) e os 12 comandos legados (`editor/commands/comandos_legados.py`) passam a reconstruir suas instâncias a partir do dicionário serializado sem realizar nenhuma consulta ao `CroquiModel`, sem `_obter_msg()`, sem `_validar_campo_se_msg_existir()`, sem consulta de buffers de imagem/anexo, sem `garantir_uids_em_mensagem()` e sem canonização de caminho durante a carga do disco. Comandos criados sem `UID` permanecem sem `UID` enquanto não sofrerem execução real de `undo`/`redo`.
- **Inferência, Serialização de `oneof` e Canonização Permanente *Lazy* na Execução**: A resolução da mensagem alvo, a inferência de `modalidade` via `DESCRIPTOR` em `CmdAlterarCampo` e a canonização permanente de `caminho_msg` para endereçamento baseado em `UID` ocorrem exclusivamente no momento da execução efetiva (`undo()`, `executar_redo()` ou `mergeWith()`). `CmdAlterarCampo` passa também a serializar e deserializar integralmente os metadados de transição de `oneof` (`var_antiga`, `valor_variante_antiga`, `var_nova`, `valor_variante_nova`).
- **Invalidação de Diários Pós-Migração**: O `GerenciadorDiario` recebe um método explícito para invalidar/limpar `diario_salvo.bin`, `diario_pendente.bin` e seus caches em memória, acionado automaticamente em `area_principal.carregar_croqui()` sempre que `aplicar_migracoes()` aplicar alguma migração pendente no disco.
- **Padronização Global de Loggers e Guarda AST**: Todos os módulos de `editor/` passam a utilizar exclusivamente `obter_logger(...)` de `editor/core/registro_log.py`, e `editor/arquitetura_mvc_test.py` adiciona uma verificação estática via AST proibindo chamadas diretas a `logging.getLogger` ou `logging.Logger` fora de `registro_log.py`.
- **Blindagem Completa dos Oráculos e Ciclo de Reabertura no Robô Caótico**: `OraculosCaos` passa a interceptar registros `ERROR`/`CRITICAL` no *root logger* (paridade 1:1 com o Sentry) e a validar `deserializar_comando()` sobre todos os registros de `diario_pendente.bin` e `diario_salvo.bin` no Oráculo 3. `MotorRoboCaoticoQt` incorpora mutações estruturais (`repeated` / `oneof`) e a ação de recarregar a sessão do croqui (`carregar_croqui()`) sobre diários persistidos, seguida de `Undo`/`Redo` auditado por hash SHA-256.

## Capabilities

### New Capabilities

### Modified Capabilities
- `undo-redo-protobuf`: Torna a deserialização de todos os comandos (canônicos e legados) 100% livre de efeitos colaterais e consultas ao modelo, adiciona persistência integral de `oneof` em `CmdAlterarCampo` e define inferência de `DESCRIPTOR` e canonização permanente de `caminho_msg` de forma estritamente *lazy* na execução (`undo`/`redo`).
- `editor-diario-recuperacao`: Adiciona a invalidação integral de `diario_salvo.bin` e `diario_pendente.bin` quando migrações automáticas alterarem os arquivos do croqui na abertura, além de garantir zero emissões de erro durante o carregamento silencioso de passos históricos intermediários.
- `arquitetura-mvc`: Adiciona regra de análise estática por AST proibindo instanciação de loggers fora da fábrica hierárquica `obter_logger` de `editor/core/registro_log.py`.
- `robo-caotico-editor-aresta`: Expande o Oráculo 1 para o *root logger*, aprofunda o Oráculo 3 para validar `deserializar_comando` nos diários binários e adiciona ações estruturais e de recarregamento de sessão (`carregar_croqui()`) na exploração da Fase B.

## Impact

- `editor/commands/comandos_protobuf.py` e `editor/commands/comandos_protobuf_test.py`
- `editor/commands/comandos_legados.py` e `editor/commands/comandos_legados_test.py`
- `editor/core/diario.py` e `editor/core/diario_test.py`
- `editor/core/historico.py` e `editor/core/historico_test.py`
- `editor/legacy_views/area_principal.py` e `editor/legacy_views/area_principal_test.py`
- `editor/plataforma/linux/integracao.py`, `editor/plataforma/linux/portal_keyring.py`, `editor/core/gerenciador_sessao.py` (padronização para `obter_logger`)
- `editor/arquitetura_mvc_test.py`
- `editor/caos/oraculos_caos.py`, `editor/caos/oraculos_caos_test.py`, `editor/caos/motor_robo_caotico.py` e `editor/caos/motor_robo_caotico_test.py`
