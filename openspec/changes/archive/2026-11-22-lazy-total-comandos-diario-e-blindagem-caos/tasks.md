# Tasks

## 1. Padronização Global de Loggers e Guarda AST

- [x] 1.1 Escrever o teste de guarda AST `test_proibicao_instanciacao_logger_fora_de_registro_log` em `editor/arquitetura_mvc_test.py` (Red), migrar `editor/commands/comandos_protobuf.py`, `editor/commands/comandos_legados.py`, `editor/core/gerenciador_sessao.py`, `editor/plataforma/linux/integracao.py` e `editor/plataforma/linux/portal_keyring.py` para `obter_logger(...)` de `editor.core.registro_log` (Green) e verificar com `uv run pytest editor/arquitetura_mvc_test.py`.

## 2. Deserialização 100% Lazy, Serialização de Oneof e Canonização Lazy nos Comandos

- [x] 2.1 Escrever testes comportamentais em `editor/commands/comandos_protobuf_test.py` e `editor/commands/comandos_legados_test.py` (Red) exigindo que a deserialização dos 7 comandos canônicos e 12 comandos legados opere sem nenhum acesso ao `CroquiModel`, sem logs `ERROR`, sem gerar novos `UID`s em mensagens sem `UID`, sem canonizar `caminho_msg` na carga, com persistência integral de `oneof` em `CmdAlterarCampo` e com canonização permanente *lazy* de `caminho_msg` exclusivamente na execução de `undo()`/`executar_redo()`/`mergeWith()`.
- [x] 2.2 Implementar o modo de deserialização pura (`_deserializado=True`), a inferência tardia de `modalidade` via `DESCRIPTOR`, a serialização completa de `oneof` e a canonização permanente *lazy* em `editor/commands/comandos_protobuf.py` e `editor/commands/comandos_legados.py` (Green), verificando 100% de cobertura comportamental com `uv run pytest editor/commands/comandos_protobuf_test.py editor/commands/comandos_legados_test.py --cov=editor.commands.comandos_protobuf --cov=editor.commands.comandos_legados --cov-fail-under=100`.
- [x] 2.3 Adicionar testes de integração em `editor/core/historico_test.py` cobrindo o ciclo completo `editar -> alterar oneof / mover / remover -> consolidar_salvamento -> carregar_diario_salvo em novo CroquiModel (zero erros de log) -> desfazer e refazer completos` e verificar 100% de cobertura com `uv run pytest editor/core/historico_test.py --cov=editor.core.historico --cov-fail-under=100`.

## 3. Invalidação de Diários Pós-Migração

- [x] 3.1 Escrever testes comportamentais em `editor/core/diario_test.py` e `editor/legacy_views/area_principal_test.py` (Red) validando `GerenciadorDiario.invalidar_historico_completo()` e a limpeza automática de `diario_salvo.bin` e `diario_pendente.bin` em `JanelaPrincipal.carregar_croqui()` quando `aplicar_migracoes` executa uma migração pendente (preservando os diários quando nenhuma migração ocorre).
- [x] 3.2 Implementar `invalidar_historico_completo()` em `editor/core/diario.py` e sua integração pós-migração em `editor/legacy_views/area_principal.py` (Green), verificando com `uv run pytest editor/core/diario_test.py editor/legacy_views/area_principal_test.py --cov=editor.core.diario --cov-fail-under=100`.

## 4. Blindagem dos Oráculos e Ciclo de Reabertura no Robô Caótico

- [x] 4.1 Escrever testes em `editor/caos/oraculos_caos_test.py` e `editor/caos/motor_robo_caotico_test.py` (Red) cobrindo a interceptação de logs `ERROR` no *root logger*, a validação de `deserializar_comando` no Oráculo 3 sobre `diario_pendente.bin` e `diario_salvo.bin`, e as novas ações de mutação estrutural (`repeated`/`oneof`) + `recarregar_sessao_croqui` seguida de `Undo`/`Redo` simétrico.
- [x] 4.2 Implementar a expansão dos oráculos em `editor/caos/oraculos_caos.py` e as ações estruturais e de recarregamento de sessão em `editor/caos/motor_robo_caotico.py` (atualizando `editor/caos/README.md`), verificando 100% de cobertura em `editor/caos/` com `uv run pytest editor/caos/ --ignore=editor/caos/robo_caotico_exploratorio_test.py --cov=editor.caos --cov-fail-under=100`.

## 5. Verificação Integrada, Tipagem Estática e Campanha de Fuzzing

- [x] 5.1 Executar verificação completa de qualidade (`ruff check`, `mypy`, `openspec validate`, suíte `pytest` integral e campanha exploratória do Robô Caótico `editor/caos/robo_caotico_exploratorio_test.py`) garantindo zero falhas e cobertura intacta.
